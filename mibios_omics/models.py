from logging import getLogger
from itertools import chain, zip_longest
import os
from subprocess import PIPE, Popen, TimeoutExpired
import sys

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.transaction import atomic

from mibios.models import Model
from mibios_umrad.fields import AccessionField
from mibios_umrad.model_utils import opt, fk_req, fk_opt
from mibios_umrad.models import Taxon
from mibios_umrad.utils import ProgressPrinter, ReturningGenerator

from .fields import DataPathField


log = getLogger(__name__)


class EOF():
    """
    End-of-file marker for file iteration
    """
    def __len__(self):
        return 0


class Bin(Model):
    history = None
    sample = models.ForeignKey('Sample', **fk_req)
    number = models.PositiveIntegerField()
    checkm = models.OneToOneField('CheckM', **fk_opt)

    method = None  # set by inheriting model

    class Meta:
        abstract = True
        unique_together = (
            ('sample', 'number'),
        )

    def __str__(self):
        return f'{self.sample.accession} {self.method} #{self.number}'

    @classmethod
    def get_concrete_models(cls):
        """
        Return list of all concrete bin sub-classes/models
        """
        # The recursion stops at the first non-abstract models, so this may not
        # make sense in a multi-table inheritance setting.
        children = cls.__subclasses__()
        if children:
            ret = []
            for i in children:
                ret += i.get_concrete_models()
            return ret
        else:
            # method called on a non-parent
            if cls._meta.abstract:
                return []
            else:
                return [cls]

    @classmethod
    def get_class(cls, method):
        """
        Get the concrete model for give binning method
        """
        if cls.method is not None:
            return super().get_class(method)

        for i in cls.get_concrete_models():
            if i.method == method:
                return i

        raise ValueError(f'not a valid binning type/method: {method}')

    @classmethod
    def import_all(cls):
        """
        Import all binning data

        This class method can be called on the abstract parent Bin class and
        will then import data for all binning types.  Or it can be called on an
        concrete model/class and then will only import data for the
        corresponding binning type.
        """
        if not cls._meta.abstract:
            raise RuntimeError(
                'method can not be called by concrete bin subclass'
            )
        for i in Sample.objects.all():
            cls.import_sample_bins(i)

    @classmethod
    def import_sample_bins(cls, sample):
        """
        Import all types of bins for given sample
        """
        if sample.binning_ok:
            log.info(f'{sample} has bins loaded already')
            return

        if cls._meta.abstract:
            # Bin parent class only
            with atomic():
                noerr = True
                for klass in cls.get_concrete_models():
                    res = klass.import_sample_bins(sample)
                    noerr = bool(res) and noerr
                if noerr:
                    sample.binning_ok = True
                    sample.save()
                return

        # Bin subclasses only
        files = list(cls.bin_files(sample))
        if not files:
            log.warning(f'no {cls.method} bins found for {sample}')
            return None

        for i in sorted(files):
            res = cls._import_bins_file(sample, i)
            if not res:
                log.warning(f'got empty cluster from {i} ??')

        return len(files)

    @classmethod
    def _import_bins_file(cls, sample, path):
        _, num, _ = path.name.split('.')
        try:
            num = int(num)
        except ValueError as e:
            raise RuntimeError(f'Failed parsing filename {path}: {e}')

        obj = cls.objects.create(sample=sample, number=num)
        cids = []
        with path.open() as f:
            for line in f:
                if not line.startswith('>'):
                    continue
                cids.append(line.strip().lstrip('>'))

        qs = ContigCluster.objects.filter(sample=sample, cluster_id__in=cids)
        kwargs = {cls._meta.get_field('members').remote_field.name: obj}
        qs.update(**kwargs)
        log.info(f'{obj} imported: {len(cids)} contig clusters')
        return len(cids)


class BinMAX(Bin):
    method = 'MAX'

    @classmethod
    def bin_files(cls, sample):
        """
        Generator over bin file paths
        """
        pat = f'{sample.accession}_{cls.method}_bins.*.fasta'
        path = settings.OMICS_DATA_ROOT / 'BINS' / 'MAX_BIN'
        return path.glob(pat)

    class Meta:
        verbose_name = 'MaxBin'
        verbose_name_plural = 'MaxBin bins'


class BinMetaBat(Bin):

    class Meta(Bin.Meta):
        abstract = True

    @classmethod
    def bin_files(cls, sample):
        """
        Generator over bin file paths
        """
        pat = f'{sample.accession}_{cls.method}_bins.*'
        path = settings.OMICS_DATA_ROOT / 'BINS' / 'METABAT'
        return path.glob(pat)


class BinMET93(BinMetaBat):
    method = 'MET_P97S93E300'

    class Meta:
        verbose_name = 'MetaBin 97/93'
        verbose_name_plural = 'MetaBin 97/93 bins'


class BinMET97(BinMetaBat):
    method = 'MET_P99S97E300'

    class Meta:
        verbose_name = 'MetaBin 99/97'
        verbose_name_plural = 'MetaBin 99/97 bins'


class BinMET99(BinMetaBat):
    method = 'MET_P99S99E300'

    class Meta:
        verbose_name = 'MetaBin 99/99'
        verbose_name_plural = 'MetaBin 99/99 bins'


class CheckM(Model):
    """
    CheckM results for a bin
    """
    history = None
    translation_table = models.PositiveSmallIntegerField(
        verbose_name='Translation table',
    )
    gc_std = models.FloatField(verbose_name='GC std')
    ambiguous_bases = models.PositiveIntegerField(
        verbose_name='# ambiguous bases',
    )
    genome_size = models.PositiveIntegerField(verbose_name='Genome size')
    longest_contig = models.PositiveIntegerField(verbose_name='Longest contig')
    n50_scaffolds = models.PositiveIntegerField(verbose_name='N50 (scaffolds)')
    mean_scaffold_len = models.FloatField(verbose_name='Mean scaffold length')
    num_contigs = models.PositiveIntegerField(verbose_name='# contigs')
    num_scaffolds = models.PositiveIntegerField(verbose_name='# scaffolds')
    num_predicted_genes = models.PositiveIntegerField(
        verbose_name='# predicted genes',
    )
    longest_scaffold = models.PositiveIntegerField(
        verbose_name='Longest scaffold',
    )
    gc = models.FloatField(verbose_name='GC')
    n50_contigs = models.PositiveIntegerField(verbose_name='N50 (contigs)')
    coding_density = models.FloatField(verbose_name='Coding density')
    mean_contig_length = models.FloatField(verbose_name='Mean contig length')

    class Meta:
        verbose_name = 'CheckM'
        verbose_name_plural = 'CheckM records'

    @classmethod
    def import_all(cls):
        for i in Sample.objects.all():
            if i.checkm_ok:
                log.info(f'sample {i}: have checkm stats, skipping')
                continue
            cls.import_sample(i)

    @classmethod
    @atomic
    def import_sample(cls, sample):
        bins = {}
        stats_file = sample.get_checkm_stats_path()
        if not stats_file.exists():
            log.warning(f'{sample}: checkm stats do not exist: {stats_file}')
            return

        for binid, obj in cls.from_file(stats_file):
            # parse binid, is like: Sample_42895_MET_P99S99E300_bins.6
            part1, _, num = binid.partition('.')  # separate number part
            parts = part1.split('_')
            sample_name = '_'.join(parts[:2])
            meth = '_'.join(parts[2:-1])  # rest but without the "_bins"

            try:
                num = int(num)
            except ValueError as e:
                raise ValueError(f'Bad bin id in stats: {binid}, {e}')

            if sample_name != sample.accession:
                raise ValueError(
                    f'Bad sample name in stats: {binid} -- expected: '
                    f'{sample.accession}'
                )

            try:
                binclass = Bin.get_class(meth)
            except ValueError as e:
                raise ValueError(f'Bad method in stats: {binid}: {e}') from e

            try:
                binobj = binclass.objects.get(sample=sample, number=num)
            except binclass.DoesNotExist as e:
                raise RuntimeError(
                    f'no bin with checkm bin id: {binid} file: {stats_file}'
                ) from e

            binobj.checkm = obj

            if binclass not in bins:
                bins[binclass] = []

            bins[binclass].append(binobj)

        for binclass, bobjs in bins.items():
            binclass.objects.bulk_update(bobjs, ['checkm'])

        sample.checkm_ok = True
        sample.save()

    @classmethod
    def from_file(cls, path):
        """
        Create instances from given bin_stats.analyze.tsv file.

        Should normally be only called from CheckM.import_sample().
        """
        ret = []
        with path.open() as fh:
            for line in fh:
                bin_key, data = line.strip().split('\t')
                data = data.lstrip('{').rstrip('}').split(', ')
                obj = cls()
                for item in data:
                    key, value = item.split(': ', maxsplit=2)
                    key = key.strip("'")
                    for i in cls._meta.get_fields():
                        if i.is_relation:
                            continue
                        # assumes correclty assigned verbose names
                        if i.verbose_name == key:
                            field = i
                            break
                    else:
                        raise RuntimeError(
                            f'Failed parsing {path}: no matching field for '
                            f'{key}, offending line is:\n{line}'
                        )

                    try:
                        value = field.to_python(value)
                    except ValidationError as e:
                        message = (f'Failed parsing field "{key}" on line:\n'
                                   f'{line}\n{e.message}')
                        raise ValidationError(
                            message,
                            code=e.code,
                            params=e.params,
                        ) from e

                    setattr(obj, field.attname, value)

                obj.save()
                ret.append((bin_key, obj))

        return ret


class SequenceLike(Model):
    """
    Abstraction of model based on fasta file sequences
    """
    history = None
    sample = models.ForeignKey('Sample', **fk_req)

    # Data from fasta file:
    # 1. offset of begin of sequence in bytes
    seq_offset = models.PositiveIntegerField(**opt)
    # 2. num of bytes until next offset (or EOF)
    seq_bytes = models.PositiveIntegerField(**opt)

    class Meta:
        abstract = True

    def get_sequence(self, fasta_format=False):
        with self.get_fasta_path(self.sample).open('rb') as fa:
            fa.seek(self.seq_offset)
            seq = b''
            for line in fa:
                if line.startswith(b'>'):
                    break
                seq += line.strip()
                if len(seq) > self.seq_bytes:
                    raise RuntimeError(
                        f'Unexpectedly, sequence of {self} has a length more '
                        f'than {self.seq_bytes}'
                    )

        if fasta_format:
            head = f'>{self}\n'
        else:
            head = ''
        return head + seq.decode()

    @classmethod
    def get_fasta_path(self, sample):
        """
        return path to fasta file that contains our sequence
        """
        # must be implemented by inheriting class
        # should return Path
        raise NotImplementedError

    @classmethod
    def have_sample_data(cls, sample, set_to=None):
        """ Check or set if a sample's data is loaded or not """
        # must be implemented by inheriting class
        # should return True or False
        raise NotImplementedError

    @classmethod
    def get_load_sample_fasta_extra_kw(cls, sample):
        """
        Return extra kwargs for from_sample_fasta()

        Should be overwritten by inherinting class if needed
        """
        return {}

    @classmethod
    def load(cls, verbose=False):
        """ Load sequence-like data for all samples """
        for i in Sample.objects.all():
            with atomic():
                if cls.have_sample_data(i):
                    log.info(f'sample {i} has assembly/mapping, skipping')
                    continue
                error = cls.load_sample(i, verbose=verbose)
                if error is not None:
                    return (i, *error)

                cls.have_sample_data(i, set_to=True)
                log.info(f'{i}: loaded {cls._meta.verbose_name_plural}')

    @classmethod
    @atomic
    def load_sample(cls, sample, limit=None, verbose=False):
        """
        import sequence data for one sample

        limit - limit to that many contigs, for testing only
        """
        extra = cls.get_load_sample_fasta_extra_kw(sample)
        objs = cls.from_sample_fasta(sample, limit=limit, verbose=verbose,
                                     **extra)
        cls.objects.bulk_create(objs)

    @classmethod
    def from_sample_fasta(cls, sample, limit=None, verbose=False, **extra):
        """
        Generate instances for given sample
        """
        print_count = verbose and sys.stdout.isatty()

        with cls.get_fasta_path(sample).open('r') as fa:
            os.posix_fadvise(fa.fileno(), 0, 0, os.POSIX_FADV_SEQUENTIAL)
            if verbose:
                print(f'reading {fa.name} ...')
            obj = None
            pp = ProgressPrinter(f'{cls._meta.verbose_name_plural} found')
            count = 0
            pos = 0
            end = EOF()
            for line in chain(fa, [end]):
                if limit and count >= limit:
                    break
                pos += len(line)
                if line is end or line.startswith('>'):
                    if obj is not None:
                        obj.seq_bytes = pos - obj.seq_offset
                        # obj.full_clean()  # way too slow
                        if print_count:
                            pp.update(count)
                        yield obj
                        count += 1

                    if line is end:
                        break

                    obj = cls(
                        sample=sample,
                        seq_offset=pos,
                    )
                    try:
                        obj.set_from_fa_head(line, **extra)
                    except Exception as e:
                        raise RuntimeError(
                            f'failed parsing fa head in file {fa.name}: '
                            f'{e.__class__.__name__}: {e}, line:\n{line}'
                        ) from e

            pp.finish()

        if verbose:
            print(f'{count} {cls._meta.verbose_name_plural} loaded')


class ContigLike(SequenceLike):
    """
    Abstract parent class for sequence like data with converage info

    This is for contigs and genes but not proteins.

    Contigs and Genes have a few things in common: fasta files with sequences
    and bbmap coverage results.  This class covers those commonalities.  There
    are a few methods that need to be implemented by the children that spell
    out the differences.  Those deal with where to find the files and different
    fasta headers.
    """
    # Data from mapping / coverage:
    # decimals in bbmap output have 4 fractional places
    # FIXME: determine max_places for sure
    length = models.PositiveIntegerField(**opt)
    bases = models.PositiveIntegerField(**opt)
    coverage = models.DecimalField(decimal_places=4, max_digits=10, **opt)
    reads_mapped = models.PositiveIntegerField(**opt)
    rpkm = models.DecimalField(decimal_places=4, max_digits=10, **opt)
    frags_mapped = models.PositiveIntegerField(**opt)
    fpkm = models.DecimalField(decimal_places=4, max_digits=10, **opt)

    class Meta:
        abstract = True

    # Name of the (per-sample) id field, must be set in inheriting class
    id_field_name = None

    @classmethod
    def process_coverage_header_data(cls, sample):
        """ Add header data to sample """
        # must be implemented by inheriting class
        return  # FIXME: !!!
        raise NotImplementedError

    @classmethod
    @atomic
    def load_sample(cls, sample, limit=None, verbose=False):
        """
        import sequence/coverage data for one sample

        limit - limit to that many contigs, for testing only
        """
        # assumes that contigs are ordered the same in objs and cov
        extra = cls.get_load_sample_fasta_extra_kw(sample)
        objs = cls.from_sample_fasta(sample, limit=limit, verbose=verbose,
                                     **extra)
        cov = cls.read_coverage(sample, limit=limit, verbose=verbose)
        cov = ReturningGenerator(cov)
        cls.objects.bulk_create(cls._join_cov_data(objs, cov))
        cls.process_coverage_header_data(cov.value)

    @classmethod
    def read_coverage(cls, sample, limit=None, verbose=False):
        """
        load coverage data

        This is a generator, yielding each row.  The return value is a dict
        with the header data.
        """
        print_count = verbose and sys.stdout.isatty()
        rpkm_cols = ['Name', 'Length', 'Bases', 'Coverage', 'Reads', 'RPKM',
                     'Frags', 'FPKM']

        head_data = {}

        with cls.get_coverage_path(sample).open('r') as f:
            os.posix_fadvise(f.fileno(), 0, 0, os.POSIX_FADV_SEQUENTIAL)
            # 1. read header
            for line in f:
                if not line.startswith('#'):
                    raise ValueError(
                        '{sample}/{f}: expected header but got: {line}'
                    )
                row = line.strip().lstrip('#').split('\t')
                if row[0] == 'Name':
                    if not row == rpkm_cols:
                        raise ValueError(
                            '{sample}/{f}: unexpected column names'
                        )
                    # table starts
                    break

                # expecting key/value pairs
                key, value = row
                head_data[key] = value

            # 2. read rows
            count = 0
            for line in f:
                if limit and count >= limit:
                    break
                yield line.rstrip().split('\t')
                count += 1
            if print_count:
                print(f'{count} coverage rows processed')

            return head_data

    @classmethod
    def _join_cov_data(cls, objs, cov):
        """ populate instances with coverage data """
        # zip_longest: ensures (over just zip) that cov.value gets populated
        for obj, row in zip_longest(objs, cov):
            myid = getattr(obj, cls.id_field_name)
            if myid not in row[0]:  # check name/id
                raise RuntimeError(
                    f'seq and cov data is out of order: {myid=} {row[0]=}'
                )

            obj.length = row[1]
            obj.bases = row[2]
            obj.coverage = row[3]
            obj.reads_mapped = row[4]
            obj.rpkm = row[5]
            obj.frags_mapped = row[6]
            obj.fpkm = row[7]

            yield obj


class ContigCluster(ContigLike):
    cluster_id = AccessionField(prefix='CLUSTER', unique=False, max_length=50)

    # bin membership
    bin_max = models.ForeignKey(BinMAX, **fk_opt, related_name='members')
    bin_m93 = models.ForeignKey(BinMET93, **fk_opt, related_name='members')
    bin_m97 = models.ForeignKey(BinMET97, **fk_opt, related_name='members')
    bin_m99 = models.ForeignKey(BinMET99, **fk_opt, related_name='members')

    class Meta:
        unique_together = (
            ('sample', 'cluster_id'),
        )

    id_field_name = 'cluster_id'

    def __str__(self):
        return self.accession

    @property
    def accession(self):
        return f'{self.sample}:{self.cluster_id}'

    @classmethod
    def have_sample_data(cls, sample, set_to=None):
        if set_to is None:
            return sample.contigs_ok
        else:
            sample.contigs_ok = set_to
            sample.save()

    @classmethod
    def get_fasta_path(cls, sample):
        return sample.get_contig_fasta_path()

    @classmethod
    def get_coverage_path(cls, sample):
        return sample.get_contig_coverage_path()

    def set_from_fa_head(self, fasta_head_line):
        # parsing ">foo\n" -> "foo"
        self.cluster_id = fasta_head_line.lstrip('>').rstrip()


class Gene(ContigLike):
    STRAND_CHOICE = (
        ('+', '+'),
        ('-', '-'),
    )
    gene_id = AccessionField(prefix='CLUSTER', unique=False, max_length=50)
    contig = models.ForeignKey('ContigCluster', **fk_req)
    start = models.PositiveIntegerField()
    end = models.PositiveIntegerField()
    strand = models.CharField(choices=STRAND_CHOICE, max_length=1)

    class Meta:
        unique_together = (
            ('sample', 'gene_id'),
        )

    id_field_name = 'gene_id'

    def __str__(self):
        return self.accession

    @property
    def accession(self):
        return f'{self.sample}:{self.gene_id}'

    @classmethod
    def have_sample_data(cls, sample, set_to=None):
        if set_to is None:
            return sample.genes_ok
        else:
            sample.genes_ok = set_to
            sample.save()

    @classmethod
    def get_fasta_path(cls, sample):
        return sample.get_gene_fasta_path()

    @classmethod
    def get_coverage_path(cls, sample):
        return sample.get_gene_coverage_path()

    @classmethod
    def get_load_sample_fasta_extra_kw(cls, sample):
        # returns a dict of the sample's contig clusters
        qs = sample.contigcluster_set.values_list('cluster_id', 'pk')
        return dict(contig_ids=dict(qs.iterator()))

    def set_from_fa_head(self, line, **kwargs):
        if 'contig_ids' in kwargs:
            contig_ids = kwargs['contig_ids']
        else:
            raise ValueError('Expect "contig_ids" in kw args')

        # parsing prodigal info
        name, start, end, strand, misc = line.lstrip('>').rstrip().split(' # ')
        cont_id, _, num = name.rpartition('_')
        try:
            int(num)
        except ValueError:
            raise

        if strand == '1':
            strand = '+'
        elif strand == '-1':
            strand = '-'
        else:
            raise ValueError('expected strand to be "1" or "-1"')

        self.gene_id = name
        self.contig_id = contig_ids[cont_id]
        self.start = start
        self.end = end
        self.strand = strand


class NCRNA(Model):
    history = None
    sample = models.ForeignKey('Sample', **fk_req)
    contig = models.ForeignKey('ContigCluster', **fk_req)
    match = models.ForeignKey('RNACentralRep', **fk_req)
    part = models.PositiveIntegerField(**opt)

    # SAM alignment section data
    flag = models.PositiveIntegerField(help_text='bitwise FLAG')
    pos = models.PositiveIntegerField(
        help_text='1-based leftmost mapping position',
    )
    mapq = models.PositiveIntegerField(help_text='MAPing Quality')

    class Meta:
        unique_together = (
            ('sample', 'contig', 'part'),
        )

    def __str__(self):
        if self.part is None:
            part = ''
        else:
            part = f'part_{self.part}'
        return f'{self.sample.accession}:{self.contig}{part}->{self.match}'

    @classmethod
    def get_sam_file(cls, sample):
        return (settings.OMICS_DATA_ROOT / 'NCRNA'
                / f'{sample.accession}_convsrna.sam')


class Protein(SequenceLike):
    gene = models.OneToOneField(Gene, **fk_req)

    def __str__(self):
        return str(self.gene)

    @classmethod
    def have_sample_data(cls, sample, set_to=None):
        if set_to is None:
            return sample.proteins_ok
        else:
            sample.proteins_ok = set_to
            sample.save()

    @classmethod
    def get_fasta_path(cls, sample):
        return (settings.OMICS_DATA_ROOT / 'PROTEINS' /
                f'{sample.accession}_PROTEINS.faa')

    @classmethod
    def get_load_sample_fasta_extra_kw(cls, sample):
        # returns a dict of the sample's genes pks
        qs = sample.gene_set.values_list('gene_id', 'pk')
        return dict(gene_ids=dict(qs.iterator()))

    def set_from_fa_head(self, line, **kwargs):
        if 'gene_ids' in kwargs:
            gene_ids = kwargs['gene_ids']
        else:
            raise ValueError('Expect "contig_ids" in kw args')

        # parsing prodigal info
        gene_accn, _, _ = line.lstrip('>').rstrip().partition(' # ')

        self.gene_id = gene_ids[gene_accn]


class ReadLibrary(Model):
    sample = models.OneToOneField(
        'Sample',
        on_delete=models.CASCADE,
        related_name='reads',
    )
    fwd_qc0_fastq = DataPathField(base='READS')
    rev_qc0_fastq = DataPathField(base='READS')
    fwd_qc1_fastq = DataPathField(base='READS')
    rev_qc1_fastq = DataPathField(base='READS')
    raw_read_count = models.PositiveIntegerField(**opt)
    qc_read_count = models.PositiveIntegerField(**opt)

    class Meta:
        verbose_name_plural = 'read libraries'

    def __str__(self):
        return self.sample.accession

    @classmethod
    @atomic
    def sync(cls, no_counts=True, raise_on_error=False):
        if not no_counts:
            raise NotImplementedError('read counting is not yet implemented')

        for i in Sample.objects.filter(reads=None):
            obj = cls.from_sample(i)
            try:
                obj.full_clean()
            except ValidationError as e:
                if raise_on_error:
                    raise
                else:
                    log.error(f'failed validation: {repr(obj)}: {e}')
                    continue
            obj.save()
            log.info(f'new read lib: {obj}')

    @classmethod
    def from_sample(cls, sample):
        obj = cls()
        obj.sample = sample
        fq = sample.get_fq_paths()
        obj.fwd_qc0_fastq = fq['dd_fwd']
        obj.rev_qc0_fastq = fq['dd_rev']
        obj.fwd_qc1_fastq = fq['ddtrnhnp_fwd']
        obj.rev_qc1_fastq = fq['ddtrnhnp_rev']
        return obj


class RNACentral(Model):
    history = None
    RNA_TYPES = (
        # unique 3rd column from rnacentral_ids.txt
        (1, 'antisense_RNA'),
        (2, 'autocatalytically_spliced_intron'),
        (3, 'guide_RNA'),
        (4, 'hammerhead_ribozyme'),
        (5, 'lncRNA'),
        (6, 'miRNA'),
        (7, 'misc_RNA'),
        (8, 'ncRNA'),
        (9, 'other'),
        (10, 'piRNA'),
        (11, 'precursor_RNA'),
        (12, 'pre_miRNA'),
        (13, 'ribozyme'),
        (14, 'RNase_MRP_RNA'),
        (15, 'RNase_P_RNA'),
        (16, 'rRNA'),
        (17, 'scaRNA'),
        (18, 'scRNA'),
        (19, 'siRNA'),
        (20, 'snoRNA'),
        (21, 'snRNA'),
        (22, 'sRNA'),
        (23, 'SRP_RNA'),
        (24, 'telomerase_RNA'),
        (25, 'tmRNA'),
        (26, 'tRNA'),
        (27, 'vault_RNA'),
        (28, 'Y_RNA'),
    )
    INPUT_FILE = (settings.OMICS_DATA_ROOT / 'NCRNA' / 'RNA_CENTRAL'
                  / 'rnacentral_clean.fasta.gz')

    accession = AccessionField()
    taxon = models.ForeignKey(Taxon, **fk_req)
    rna_type = models.PositiveSmallIntegerField(choices=RNA_TYPES)

    def __str__(self):
        return (f'{self.accession} {self.taxon.taxid} '
                f'{self.get_rna_type_display()}')

    @classmethod
    def load(cls, path=INPUT_FILE):
        type_map = dict(((b.casefold(), a) for a, b, in cls.RNA_TYPES))
        taxa = dict(Taxon.objects.values_list('taxid', 'pk'))

        zcat_cmd = ['/usr/bin/unpigz', '-c', str(path)]
        zcat = Popen(zcat_cmd, stdout=PIPE)

        pp = ProgressPrinter('rna central records read')
        objs = []
        try:
            print('BORK STAGE I')
            for line in zcat.stdout:
                # line is bytes
                if not line.startswith(b'>'):
                    continue
                line = line.decode()
                accn, typ, taxid2, _ = line.lstrip('>').split('|', maxsplit=4)
                # taxid2 can be multiple, so take taxid from accn (ask Teal?)
                accn, _, taxid = accn.partition('_')
                objs.append(cls(
                    accession=accn,
                    taxon_id=taxa[int(taxid)],
                    rna_type=type_map[typ.lower()],
                ))
                pp.inc()
        except Exception:
            raise
        finally:
            try:
                zcat.communicate(timeout=15)
            except TimeoutExpired:
                zcat.kill()
                zcat.communicate()
            if zcat.returncode:
                log.error(f'{zcat_cmd} returned with status {zcat.returncode}')

        pp.finish()
        log.info(f'Saving {len(objs)} RNA Central accessions...')
        cls.objects.bulk_create(objs)


class RNACentralRep(Model):
    """ Unique RNACentral representatives """
    history = None


class Sample(Model):
    accession = AccessionField()

    # data accounting
    contigs_ok = models.BooleanField(
        default=False,
        help_text='Contig cluster data and coverage loaded',
    )
    binning_ok = models.BooleanField(
        default=False,
        help_text='Binning data loaded',
    )
    checkm_ok = models.BooleanField(
        default=False,
        help_text='Binning stats loaded',
    )
    genes_ok = models.BooleanField(
        default=False,
        help_text='Gene data and coverage loaded',
    )
    proteins_ok = models.BooleanField(
        default=False,
        help_text='Protein data loaded',
    )

    # mapping data (from ASSEMBLIES/COVERAGE)
    read_count = models.PositiveIntegerField(
        **opt,
        help_text='number of reads used for assembly mapping',
    )
    reads_mapped = models.PositiveIntegerField(
        **opt,
        help_text='number of reads mapped to assembly',
    )
    num_ref_sequences = models.PositiveIntegerField(
        **opt,
        help_text='RefSequences number in coverage file header',
    )

    def __str__(self):
        return self.accession

    @classmethod
    @atomic
    def sync(cls, sample_list='sample_list.txt', **kwargs):
        src = settings.OMICS_DATA_ROOT / sample_list
        with open(src) as f:
            seen = []
            for line in f:
                obj, isnew = cls.objects.get_or_create(
                    accession=line.strip()
                )
                seen.append(obj.pk)
                if isnew:
                    log.info(f'new sample: {obj}')

        not_in_src = cls.objects.exclude(pk__in=seen)
        if not_in_src.exists():
            log.warning(f'Have {not_in_src.count()} extra samples in DB not '
                        f'found in {src}')

    @classmethod
    def status(cls):
        if not cls.objects.exists():
            print('no samples in database yet')
            return

        print(' ' * 10, 'contigs', 'bins', 'checkm', 'genes', sep='\t')
        for i in cls.objects.all():
            print(
                f'{i}:',
                'OK' if i.contigs_ok else '',
                'OK' if i.binning_ok else '',
                'OK' if i.checkm_ok else '',
                'OK' if i.genes_ok else '',
                sep='\t'
            )

    @classmethod
    def status_long(cls):
        if not cls.objects.exists():
            print('no samples in database yet')
            return

        print(' ' * 10, 'cont cl', 'MAX', 'MET93', 'MET97', 'MET99', 'genes',
              sep='\t')
        for i in cls.objects.all():
            print(
                f'{i}:',
                i.contigcluster_set.count(),
                i.binmax_set.count(),
                i.binmet93_set.count(),
                i.binmet97_set.count(),
                i.binmet99_set.count(),
                i.gene_set.count(),
                sep='\t'
            )

    def load_bins(self):
        if not self.binning_ok:
            with atomic():
                Bin.import_sample_bins(self)
                self.binning_ok = True
                self.save()
        if self.binning_ok and not self.checkm_ok:
            with atomic():
                CheckM.import_sample(self)
                self.checkm_ok = True
                self.save()

    @atomic
    def delete_bins(self):
        with atomic():
            qslist = [self.binmax_set, self.binmet93_set, self.binmet97_set,
                      self.binmet99_set]
            for qs in qslist:
                print(f'{self}: deleting {qs.model.method} bins ...', end='',
                      flush=True)
                counts = qs.all().delete()
                print('\b\b\bOK', counts)
            self.binning_ok = False
            self.checkm_ok = False  # was cascade-deleted
            self.save()

    def get_contig_fasta_path(self):
        return (
            settings.OMICS_DATA_ROOT / 'ASSEMBLIES' / 'MERGED'
            / (self.accession + '_MCDD.fa')
        )

    def get_gene_fasta_path(self):
        return (
            settings.OMICS_DATA_ROOT / 'GENES'
            / (self.accession + '_GENES.fna')
        )

    def get_contig_coverage_path(self, filetype='rpkm'):
        fnames = {
            'rpkm': f'{self.accession}_READSvsCONTIGS.rpkm',
            'max': f'{self.accession}_MAX_coverage.txt',
            'met': f'{self.accession}_MET_coverage.txt',
        }
        base = settings.OMICS_DATA_ROOT / 'ASSEMBLIES' / 'COVERAGE'
        try:
            return base / fnames[filetype.casefold()]
        except KeyError as e:
            raise ValueError(f'unknown filetype: {filetype}') from e

    def get_gene_coverage_path(self):
        return (settings.OMICS_DATA_ROOT / 'GENES' / 'COVERAGE'
                / f'{self.accession}_READSvsGENES.rpkm')

    def get_fq_paths(self):
        base = settings.OMICS_DATA_ROOT / 'READS'
        fname = f'{self.accession}_{{infix}}.fastq.gz'
        return {
            infix: base / fname.format(infix=infix)
            for infix in ['dd_fwd', 'dd_rev', 'ddtrnhnp_fwd', 'ddtrnhnp_rev']
        }

    def get_checkm_stats_path(self):
        return (settings.OMICS_DATA_ROOT / 'BINS' / 'CHECKM'
                / f'{self.accession}_CHECKM' / 'storage'
                / 'bin_stats.analyze.tsv')


def load_all(**kwargs):
    """
    Load all data

    assumes an empty DB.
    """
    verbose = kwargs.get('verbose', False)
    Sample.sync(**kwargs)
    # ReadLibrary.sync()
    ContigCluster.load(verbose=verbose)
    Bin.import_all()
    CheckM.import_all()
    Gene.load(verbose=verbose)
    Protein.load(verbose=verbose)