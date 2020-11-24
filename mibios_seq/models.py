from collections import OrderedDict
from itertools import chain, groupby
from operator import attrgetter, itemgetter

from Bio import SeqIO
from django.db import models
from django.db.transaction import atomic

from omics.shared import MothurShared
from mibios.dataset import UserDataError
from mibios.models import (ImportFile, Manager, CurationManager, Model,
                           ParentModel, QuerySet, TagNote)
from mibios.utils import getLogger


log = getLogger(__name__)


class Sample(ParentModel):
    """
    Parent model for samples

    This is the multi-table-inheritance parent that other apps should use to
    interface with sequencing data.  There are no fields declared here besides
    the usual auto-primary-key and history.
    """
    pass


class Sequencing(Model):
    MOCK = 'mock'
    WATER = 'water'
    BLANK = 'blank'
    PLATE = 'plate'
    OTHER = 'other'
    CONTROL_CHOICES = (
        (MOCK, MOCK),
        (WATER, WATER),
        (BLANK, BLANK),
        (PLATE, PLATE),
        (OTHER, OTHER),
    )
    name = models.CharField(max_length=100, unique=True)
    sample = models.ForeignKey(Sample, on_delete=models.SET_NULL,
                               blank=True, null=True)
    control = models.CharField(max_length=50, choices=CONTROL_CHOICES,
                               blank=True)
    r1_file = models.CharField(max_length=300, unique=True, blank=True,
                               null=True)
    r2_file = models.CharField(max_length=300, unique=True, blank=True,
                               null=True)
    note = models.ManyToManyField(TagNote, blank=True)
    run = models.ForeignKey('SequencingRun', on_delete=models.CASCADE,
                            blank=True, null=True)
    plate = models.PositiveSmallIntegerField(blank=True, null=True)
    plate_position = models.CharField(max_length=10, blank=True)
    snumber = models.PositiveSmallIntegerField(blank=True, null=True)
    otu = models.ManyToManyField(
        'OTU',
        through='Abundance',
        editable=False,
    )

    class Meta:
        unique_together = (
            ('run', 'snumber'),
            ('run', 'plate', 'plate_position'),
        )
        ordering = ['name']

    @classmethod
    def parse_control(cls, txt):
        """
        Coerce text into available control choices
        """
        choice = txt.strip().lower()
        if choice:
            for i in (j[0] for j in cls.CONTROL_CHOICES):
                if i in choice:
                    return i
            return cls.OTHER
        else:
            return ''


class SequencingRun(Model):
    serial = models.CharField(max_length=50)
    number = models.PositiveSmallIntegerField()
    path = models.CharField(max_length=2000, blank=True)

    class Meta:
        unique_together = ('serial', 'number')
        ordering = ['serial', 'number']

    @Model.natural.getter
    def natural(self):
        return '{}-{}'.format(self.serial, self.number)

    @classmethod
    def natural_lookup(cls, value):
        if value is cls.NOT_A_VALUE:
            s, n = None, None
        else:
            s, n = value.split('-')
            n = int(n)
        return dict(serial=s, number=n)


class Sequence(Model):
    """
    Models a 16S/V4 sequence

    Can be an ASV or a representative sequence
    """
    taxon = models.ForeignKey('Taxonomy', on_delete=models.SET_NULL,
                              blank=True, null=True)
    seq = models.CharField(
        max_length=300,  # >> length of 16S V4
        unique=True,
        editable=False,
        verbose_name='sequence',
    )

    def __str__(self):
        return self.seq[:20] + '...'


class Strain(Model):
    sequence = models.ForeignKey(Sequence, on_delete=models.SET_NULL,
                                 blank=True, null=True)


class AbundanceQuerySet(QuerySet):
    def as_shared(self):
        """
        Make mothur-shared table

        Note: without label/numOtus columns

        Returns a pandas DataFrame.  Assumes, that the QuerySet is filtered to
        counts from a single analysis project but this is not checked.  If the
        assumption is violated, then the pivot operation will probably raise a:

            "ValueError: Index contains duplicate entries, cannot reshape"

        Missing counts are inserted as zero, mirroring the skipping of zeros at
        import.

        DEPRECATED (and possibly incorrect)
        """
        df = (
            self
            .as_dataframe('otu', 'sequencing', 'count', natural=True)
            .pivot(index='sequencing', columns='otu', values='count')
        )
        df.fillna(value=0, inplace=True)  # pivot introduced NaNs
        return df

    def as_shared_values_list_old(self):
        """
        Make mothur-shared table (slow, memory intense version)

        Returns an iterator over tuple rows, first row is the header.  This is
        intended to support data export.

        DEPRECATED (and possibly incorrect)
        """
        sh = self.as_shared()
        header = ['Group'] + list(sh.columns)
        recs = sh.itertuples(index=True, name=None)
        return chain([header], recs)

    @classmethod
    def _normalize(cls, group, size, debug=0):
        """
        Scale absolute counts to normal sample size
        """
        group = list(group)
        debug <= 1 or print(f'group={group}')
        vals = [i[0] for i in group]
        debug <= 1 or print(f'vals={vals}')
        total = sum(vals)
        debug <= 0 or print(f'total={total}')
        f = size / total
        frac = [i * f for i in vals]
        debug <= 1 or print(f'frac={frac}')
        disc = [round(i) for i in frac]
        overhang = sum(disc) - size
        debug <= 0 or print(f'overhang={overhang}')
        for _ in range(abs(overhang)):
            errs = [i - j for i, j in zip(disc, frac)]  # round-up errs are pos
            debug <= 1 or print(f'dict={disc} at {sum(disc)}')
            debug <= 1 or print(f'errs={errs}')
            if overhang > 0:
                abs_err_max = max(errs)
            else:
                abs_err_max = min(errs)
            idx = errs.index(abs_err_max)
            if overhang > 0:
                disc[idx] -= 1
            else:
                disc[idx] += 1
            debug <= 0 or print(f'idx={idx} count={disc[idx]} err: '
                                '{errs[idx]}->{disc[idx]-frac[idx]}')
        debug <= 1 or print(f'disc={disc} at {sum(disc)}')
        debug <= 1 or print(sum(disc))
        return ((i, j, k) for i, (_, j, k) in zip(disc, group))

    @classmethod
    def test_norm(cls, vals, norm_size, verbose=False, verboser=False):
        if verboser:
            debug = 2
        elif verbose:
            debug = 1
        else:
            debug = 0
        ret = cls._normalize(
            ((i, None, None) for i in vals),
            norm_size,
            debug=debug,
        )
        if not verboser:
            print([i[0] for i in ret])

    @classmethod
    def _unit_normalize(cls, group):
        """
        Normalize to unit interval, return fractions

        This gets fractions from absolute counts, but is not needed if relative
        abundance is sotred in the DB.
        """
        group = list(group)
        vals = [i[0] for i in group]
        total = sum(vals)
        return ((i / total, j, k) for i, j, k in group)

    def _shared_file_items(self, otus, group, normalize):
        """
        Generator over the items of a row in a shared file

        This fills in zeros as needed.

        :param otus: iterable over all ASV pks of QuerySet in order
        :param group: Data for one sample, row; an iterable over tuple
                      (abund, OTU pk)
        """
        if normalize == 0:
            zero = 0.0
        else:
            zero = 0

        abund, otu_pk = next(group)
        for i in otus:
            if otu_pk == i:
                yield abund
                try:
                    abund, otu_pk = next(group)
                except StopIteration:
                    pass
            else:
                yield zero

    def _shared_file_rows(self, otus, normalize, groupids, mothur):
        """
        Generator of shared file rows

        :param int normalize: Normalization mode.  If None then absolute counts
        are returned.  If 0 then relative abundance, as fractional values in
        [0, 1] are returned.  If an integer above 0 is given, then the counts
        are normalized by 'discrete scaling' to the targeted sample size.
        """
        if normalize is None:
            abund_field = 'count'
        else:
            abund_field = 'relative'

        if self._avg_by:
            id_fields = [
                i for i in self._avg_by
                if i not in ['project', 'otu']
            ]
        else:
            id_fields = ['sequencing']
        it = (
            self.order_by(*id_fields, 'otu')
            .values_list(abund_field, 'otu', *id_fields)
            .iterator()
        )

        # Group data by what will be the rows of the shared file.  Map row
        # ids/sequencing name to whatever grouids() says and process the
        # rest, which are now tuples of abundance value and otu, in two
        # steps: (1) possibly normalize the values and (2) fill in the
        # zeros.  Then that gets packaged into a row, each of which is
        # yielded back.
        rm_ids = itemgetter(0, 1)
        for row_id, group in groupby(it, key=itemgetter(slice(2, None))):
            # row_id is tuple of id_fields from above
            try:
                group_id_vals = groupids(*row_id)
            except LookupError:
                group_id_vals = [f'{i}:{j}' for i, j in zip(id_fields, row_id)]
            group = map(rm_ids, group)
            if normalize is not None and normalize >= 1:
                group = ((round(i[0] * normalize), i[1]) for i in group)

            values = self._shared_file_items(otus, group, normalize)
            yield tuple(chain(group_id_vals, values))

    def as_shared_values_list(
            self,
            normalize=None,
            groupids=lambda x: x,
            group_cols_verbose=('Group', ),
            mothur=False,
    ):
        """
        Make mothur shared table for download

        Returns an iterator over tuple rows, first row is the header.  This is
        intended to support data export.  Missing counts are inserted as zero,
        mirroring the skipping of zeros at import.

        This method will happily return data from multiple analysis projects.
        This makes little sense in the shared-data-export context and the
        caller should ensure that the query set is properly filtered.
        """
        if mothur:
            raise ValueError('Mothur mode is not implement')

        # get OTUs that actually occur in QuerySet:
        otu_pks = set(self.values_list('otu', flat=True).distinct().iterator())
        # OTU order here must correspond to order in which count values are
        # generated later, in the _shared_file_rows() method.  It is assumed
        # that the OTU model defines an appropriate order; OTU pk->name
        # mapping, use values for header, keys for zeros injection
        otus = OrderedDict((
            (i.pk, i.natural)
            for i in OTU.objects.iterator()
            if i.pk in otu_pks
        ))

        # Build header row:
        if mothur:
            header = ['label', 'Group', 'numOtus']
        else:
            header = list(group_cols_verbose)
        header += list(otus.values())

        return chain([header], self._shared_file_rows(
            list(otus.keys()),
            normalize,
            groupids,
            mothur,
        ))


class Abundance(Model):
    """
    Models read count

    *** HOWTO add data from an analysis run ***

    (1) create a new AnalysisProject record.
    (2) For a mothur SOP 97% OTU run, abundances only, no sequences, you need
        these files:

        ugrads19.asv0.precluster.pick.opti_mcc.shared
        ugrads19.asv0.precluster.pick.opti_mcc.0.03.rep.fasta
        ugrads19.asv0.precluster.pick.opti_mcc.0.03.cons.taxonomy

    (3) Then in the shell, run:

      1 from mibios_seq.models import Abundance, AnalysisProject
      2 p = AnalysisProject.objects.get(name='mothur_SOP_97pct')
      3 Abundance.from_file(
            'ugrads19.final.shared',
            project=p,
            fasta='ugrads19.final.fa'
        )
    """
    history = None
    otu = models.ForeignKey(
        'OTU',
        on_delete=models.CASCADE,
        editable=False,
        verbose_name='OTU',
    )
    count = models.PositiveIntegerField(
        help_text='absolute abundance',
        editable=False,
    )
    relative = models.FloatField(
        default=None, null=True,
        verbose_name='relative abundance',
        editable=False,
    )
    sequencing = models.ForeignKey(
        Sequencing,
        on_delete=models.CASCADE,
        editable=False,
    )
    project = models.ForeignKey(
        'AnalysisProject',
        on_delete=models.CASCADE,
        editable=False,
        verbose_name='analysis project',
    )

    class Meta:
        unique_together = (
            # one count per project / OTU / sample
            ('otu', 'sequencing', 'project'),
        )
        verbose_name_plural = 'abundance'

    objects = Manager.from_queryset(AbundanceQuerySet)()
    curated = CurationManager.from_queryset(AbundanceQuerySet)()

    average_by = [('project', 'otu',
                   'sequencing__sample__fecalsample__participant',
                   'sequencing__sample__fecalsample__week')]
    average_fields = ['relative']

    def __str__(self):
        return super().__str__() + f' |{self.count}|'

    @classmethod
    def from_file(cls, file, project, fasta=None, threads=1):
        """
        Load abundance data from shared file

        :param file fasta: Fasta file object
        :param str otu_type: A valid OTU type.

        If a fasta file is given, then the input does not need to use proper
        ASV numbers.  Instead ASVs are identified by sequence and ASV objects
        are created as needed.  Obviously, the OTU/ASV/sequence names in shared
        and fasta files must correspond.
        """
        sh = MothurShared(file, verbose=False, threads=threads)
        return cls._from_file(file, project, fasta, sh)

    @classmethod
    @atomic
    def _from_file(cls, file, project, fasta, sh):
        if fasta:
            fasta_result = OTU.from_fasta(fasta, project=project)
        else:
            fasta_result = None
        AbundanceImportFile.create_from_file(file=file, project=project)
        sequencings = Sequencing.objects.in_bulk(field_name='name')
        if project.otu_type == AnalysisProject.ASV_TYPE:
            f = dict(project=None)
        else:
            f = dict(project=project)
        otus = {
            (i.prefix, i.number): i
            for i in OTU.objects.all().filter(**f).iterator()
        }
        del f

        skipped, zeros, otus_new = 0, 0, 0
        objs = []
        for (seqid, otu), count in sh.counts.stack().items():
            if count == 0:
                # don't store zeros
                zeros += 1
                continue

            if seqid not in sequencings:
                # ok to skip, e.g. non-public
                skipped += 1
                continue

            try:
                otu_key = OTU.natural_lookup(otu)
            except ValueError:
                raise UserDataError(
                    f'Irregular OTU identifier not supported: {otu}'
                )
            else:
                otu_key = (otu_key['prefix'], otu_key['number'])

            try:
                otu_obj = otus[otu_key]
            except KeyError:
                otu_obj = OTU.objects.create(
                    prefix=otu_key[0],
                    number=otu_key[1],
                    project=project,
                )
                otus[otu_key] = otu_obj
                otus_new += 1

            objs.append(cls(
                count=count,
                project=project,
                sequencing=sequencings[seqid],
                otu=otu_obj,
            ))

        cls.objects.bulk_create(objs)
        return dict(count=len(objs), zeros=zeros, skipped=skipped,
                    fasta=fasta_result, otus_created=otus_new)

    @classmethod
    def compute_relative(cls, project=None):
        """
        Compute values for the relative abundance field

        :param project: Restrict calculations to given project

        This will overwrite existing data.  If case of errors, partial updates
        are possible.
        """
        qs = (cls.objects
              .select_related('project', 'sequencing')
              .order_by('project__pk', 'sequencing__pk'))

        if project:
            qs = qs.filter(project=project)

        grpkey = attrgetter('project.pk', 'sequencing.pk')
        for _, group in groupby(qs.iterator(), key=grpkey):
            group = list(group)
            total = sum((i.count for i in group))
            for i in group:
                i.relative = i.count / total
            cls.objects.bulk_update(group, ('relative', ))

    @classmethod
    def compare_projects(cls, project_a, project_b):
        """
        Compare absolute counts between two ASV analysis projects
        """
        total = 0
        skipped = 0
        same = 0
        diffs = {}
        qs = cls.objects.filter(project__in=[project_a, project_b])
        qs = qs.order_by('sequencing', 'otu', 'project')

        def keyfun(obj):
            return (obj.sequencing, obj.otu)

        for (seq, otu), grp in groupby(qs, key=keyfun):
            grp = list(grp)
            if len(grp) == 1:
                skipped += 1
                continue
            if len(grp) > 2:
                raise RuntimeError('expected at most two in group')

            total += 1
            delta = grp[1].count - grp[0].count
            if delta == 0:
                same += 1
                continue

            pct = abs(delta) / max(grp[0].count, grp[1].count)
            diffs[(seq, otu)] = (delta, pct)

        return dict(
            total=total,
            skipped=skipped,
            same=same,
            diffs=diffs,
        )


class AnalysisProject(Model):
    ASV_TYPE = 'ASV'
    PCT97_TYPE = '97pct'
    OTU_TYPE_CHOICES = (
        (ASV_TYPE, 'ASV'),
        (PCT97_TYPE, '97% OTU'),
    )

    name = models.CharField(max_length=100, unique=True)
    otu = models.ManyToManyField('OTU', through=Abundance, editable=False)
    sequencing = models.ManyToManyField(Sequencing, through=Abundance,
                                        editable=False, related_name='project')
    otu_type = models.CharField(max_length=5, choices=OTU_TYPE_CHOICES,
                                verbose_name='OTU type')
    description = models.TextField(blank=True)

    @classmethod
    def get_fields(cls, with_m2m=False, **kwargs):
        # Prevent numbers from being displayed, too much data
        return super().get_fields(with_m2m=False, **kwargs)


class OTU(Model):
    NUM_WIDTH = 5

    prefix = models.CharField(max_length=8)
    number = models.PositiveIntegerField()
    project = models.ForeignKey('AnalysisProject', on_delete=models.CASCADE,
                                related_name='owned_otus',
                                null=True, blank=True)
    sequence = models.ForeignKey(
        Sequence,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        editable=False,
    )

    hidden_fields = ['prefix', 'number']  # use name property instead

    class Meta:
        ordering = ('prefix', 'number',)
        unique_together = (('prefix', 'number', 'project'),)
        verbose_name = 'OTU'

    def __str__(self):
        return str(self.natural)
        s = str(self.natural)
        if self.taxon:
            genus, _, species = self.taxon.name.partition(' ')
            if species:
                genus = genus.lstrip('[')[0].upper() + '.'
                s += ' ' + genus + ' ' + species
            else:
                s += ' ' + str(self.taxon)

        return s

    @property
    def name(self):
        return str(self.natural)

    @Model.natural.getter
    def natural(self):
        return self.prefix + '{}'.format(self.number).zfill(self.NUM_WIDTH)

    @classmethod
    def natural_lookup(cls, value):
        """
        Given e.g. ASV00023, return dict(number=23)

        Raises ValueError if value does not end with a number.
        Raises KeyError if value has no non-numeric prefix.
        """
        if value is cls.NOT_A_VALUE:
            return dict(prefix=None, number=None)

        places = 0
        while value[-1 - places].isdecimal():
            places += 1

        number = int(value[-places:])
        prefix = value[:-places]
        return dict(prefix=prefix, number=number)

    @classmethod
    @atomic
    def from_fasta(cls, file, project=None):
        """
        Import from given fasta file

        :param file: Fasta-formatted input file
        :param AnalysisProject project: AnalysisProject that generated the OTUs
                                        If this is None, then the OTU type will
                                        be set to ASV.
        """
        file_rec = ImportFile.create_from_file(file=file)

        try:
            file_rec.file.open('r')
            return cls._from_fasta(file_rec, project)
        except Exception:
            try:
                file_rec.file.close()
                file_rec.file.delete()
            except Exception:
                pass
            raise
        else:
            file_rec.file.close()

    @classmethod
    def _from_fasta(cls, file_rec, project):
        added, updated, skipped, total = 0, 0, 0, 0
        seq_added = 0

        # passing the filehandle to SeqIO.parse: The SeqIO fasta parser tries
        # to skip over comments and empty lines at the begin of the file by
        # iterating over the passed file handle.  After the first line with '>'
        # is found, the line is kept and then it breaks out of the for loop and
        # enters another for loop over the file handle iterator to get the rest
        # of the data.  When we pass a django.core.files.base.File object the
        # second loop entry calls a seek(0) as part of the chunking machinery
        # and it gets messy.  This is why we pass the underlying file object
        # and hope this won't blow up when something about the file storage
        # changes.
        for i in SeqIO.parse(file_rec.file.file.file, 'fasta'):
            try:  # expect {'prefix': X, 'number': N}
                kwnum = cls.natural_lookup(i.id)
            except ValueError:
                # SeqIO sequence id does not parse,
                # is something from analysis pipeline, no OTU number?
                skipped += 1
                continue

            seq, new_seq = Sequence.objects.get_or_create(seq=i.seq)
            if new_seq:
                seq_added += 1

            if project and project.otu_type == project.ASV_TYPE:
                # ASVs do not belong to a project
                project = None

            obj_kw = dict(
                prefix=kwnum['prefix'],
                number=kwnum['number'],
                project=project,
            )
            has_changed = False
            try:
                obj = cls.objects.get(**obj_kw)
            except cls.DoesNotExist:
                obj = cls(sequence=seq, **obj_kw)
                added += 1
                has_changed = True
            else:
                if obj.sequence is None:
                    obj.sequence = seq
                    updated += 1
                    has_changed = True
                elif obj.sequence != seq:
                    raise UserDataError(f'OTU record already exists with'
                                        f'different sequence: {obj}')

            if has_changed:
                try:
                    obj.full_clean()
                except Exception as e:
                    log.error('Failed importing ASV: at fasta record '
                              f'{total + 1}: {i}: {e}')
                    raise

                obj.add_change_record(file=file_rec, line=total + 1)
                obj.save()

            total += 1

        return dict(total=total, new=added, updated=updated,
                    skipped=skipped)


class Taxonomy(Model):
    taxid = models.PositiveIntegerField(
        unique=True,
        verbose_name='NCBI taxonomy id',
    )
    name = models.CharField(
        max_length=300,
        unique=True,
        verbose_name='taxonomic name',
    )

    class Meta:
        verbose_name_plural = 'taxonomy'

    def __str__(self):
        return '{} ({})'.format(self.name, self.taxid)

    @classmethod
    @atomic
    def from_blast_top1(cls, file):
        """
        Import from blast-result-top-1 format file

        The supported file format is a tab-delimited text file with header row,
        column 1 are ASV accessions, columns 5 and 6 are NCBI taxids and names,
        and if there are ties then column 7 are the least-common NCBI taxids
        and column 8 are the corresponding taxon names

        The taxonomy for existing ASV records is imported, everything else is
        ignored.
        """
        file_rec = ImportFile.create_from_file(file=file)
        otus = {(i.prefix, i.number): i for i in OTU.objects.select_related()}
        is_header = True  # first line is header
        updated, total = 0, 0
        for line in file_rec.file.open('r'):
            if is_header:
                is_header = False
                continue

            try:
                total += 1
                row = line.rstrip('\n').split('\t')
                asv, taxid, name, lctaxid, lcname = row[0], *row[4:]

                if lcname and lcname:
                    name = lcname
                    taxid = lctaxid

                taxid = int(taxid)
                match = OTU.natural_lookup(asv)
                prefix = match['prefix']
                num = match['number']
                del match

                if (prefix, num) not in otus:
                    # ASV not in database
                    continue

                try:
                    taxon = cls.objects.get(taxid=taxid, name=name)
                except cls.DoesNotExist:
                    taxon = cls(taxid=taxid, name=name)
                    taxon.full_clean()
                    taxon.add_change_record(file=file_rec, line=total + 1)
                    taxon.save()

                if otus[num].taxon == taxon:
                    del otus[num]
                else:
                    otus[num].taxon = taxon
                    updated += 1
            except Exception as e:
                raise RuntimeError(
                    f'error loading file: {file} at line {total}: {row}'
                ) from e

        OTU.objects.bulk_update(otus.values(), ['taxon'])
        return dict(total=total, update=updated)


class AbundanceImportFile(ImportFile):
    """
    An import file that keeps tab to which project it belongs

    Since Abundance opts out of history this connecting the import file with
    the project keeps at leas some record of the origin of abundance data.
    """
    project = models.ForeignKey(AnalysisProject, on_delete=models.CASCADE)
