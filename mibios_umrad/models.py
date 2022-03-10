from collections import OrderedDict, defaultdict
from itertools import islice, zip_longest
from logging import getLogger
from pathlib import Path

from django.conf import settings
from django.core.exceptions import FieldDoesNotExist
from django.db import models
from django.db.transaction import atomic, set_rollback
from django.utils.functional import cached_property

from mibios import get_registry

from .fields import AccessionField
from . import manager
from .model_utils import (
    ch_opt, fk_opt, fk_req, VocabularyModel, delete_all_objects_quickly,
    LoadMixin, Manager, Model
)
from .utils import CSV_Spec


log = getLogger(__name__)


class CompoundEntryManager(Manager):
    def create_from_m2m_input(self, values, source_model, src_field_name):
        if source_model is UniRef100 and src_field_name == 'trans_compounds':
            pass
        else:
            raise NotImplementedError(
                'is only implemented for field UniRef100.trans_compound'
            )

        # create one unique reaction group per value
        try:
            last_pk = Compound.objects.order_by('pk').latest('pk').pk
        except Compound.DoesNotExist:
            last_pk = -1
        Compound.objects.bulk_create(
            (Compound() for _ in range(len(values))),
            batch_size=500  # runs up at SQLITE_MAX_COMPOUND_SELECT,django bug?
        )
        cpd_pks = Compound.objects.filter(pk__gt=last_pk)\
                          .values_list('pk', flat=True)
        if len(values) != len(cpd_pks):
            # just checking
            raise RuntimeError('a bug making right number of Compound objects')

        model = self.model
        db = CompoundEntry.DB_CHEBI
        objs = (model(accession=i, db=db, compound_id=j)
                for i, j in zip(values, cpd_pks))
        return self.bulk_create(objs)


class CompoundEntry(Model):
    """ Reference DB's entry for chemical compound, reactant, or product """
    DB_BIOCYC = 'b'
    DB_CHEBI = 'c'
    DB_HMDB = 'h'
    DB_INCHI = 'i'
    DB_KEGG = 'k'
    DB_PUBCHEM = 'p'
    DB_CHOICES = (
        (DB_BIOCYC, 'Biocyc'),
        (DB_CHEBI, 'ChEBI'),
        (DB_HMDB, 'HMDB'),
        (DB_INCHI, 'InChi'),
        (DB_KEGG, 'KEGG'),
        (DB_PUBCHEM, 'PubChem'),
    )

    accession = models.CharField(max_length=40, unique=True)
    db = models.CharField(max_length=1, choices=DB_CHOICES, db_index=True)
    formula = models.CharField(max_length=32, blank=True)
    charge = models.SmallIntegerField(blank=True, null=True)
    mass = models.CharField(max_length=16, blank=True)  # TODO: decimal??
    names = models.ManyToManyField('CompoundName')
    compound = models.ForeignKey(
        'Compound',
        **fk_req,
        related_name='group',
        verbose_name='distinct compound',
    )

    objects = CompoundEntryManager()

    def __str__(self):
        return self.accession

    def group(self):
        """ return QuerySet of synonym/related compound entry group """
        return self.compound.group.all()

    external_urls = {
        DB_BIOCYC: 'https://biocyc.org/compound?orgid=META&id={}',
        DB_CHEBI: 'https://www.ebi.ac.uk/chebi/searchId.do?chebiId={}',
        DB_HMDB: 'https://hmdb.ca/metabolites/{}',
        DB_INCHI: (
            'https://www.ebi.ac.uk/unichem/frontpage/results?queryText={}&kind=InChIKey',  # noqa: E501
            lambda x: x.removeprefix('INCHI:')
        ),
        DB_KEGG: 'https://www.kegg.jp/entry/{}',
        DB_PUBCHEM: (
            'https://pubchem.ncbi.nlm.nih.gov/compound/{}',
            lambda x: x.removeprefix('CID:')
        ),
    }

    def get_external_url(self):
        url_spec = self.external_urls[self.db]
        if not url_spec:
            return None
        elif isinstance(url_spec, str):
            # assume simple formatting string
            return url_spec.format(self.accession)
        else:
            # assumme a tuple (templ, func)
            return url_spec[0].format(url_spec[1](self.accession))


class Compound(Model):
    """ Distinct source-DB-independent compounds """

    # no fields hereQ

    loader = manager.CompoundLoader()

    class Meta:
        verbose_name = 'distinct compound'

    # spec: 2nd item is either base compound field name or compound model name
    # for the reverse relation
    loader_spec = CSV_Spec(
        ('id', 'accession'),
        ('form', 'formula'),
        ('char', 'charge'),
        ('mass', 'mass'),
        ('hmdb', CompoundEntry.DB_HMDB),
        ('inch', CompoundEntry.DB_INCHI),
        ('bioc', CompoundEntry.DB_BIOCYC),
        ('kegg', CompoundEntry.DB_KEGG),
        ('pubc', CompoundEntry.DB_PUBCHEM),
        ('cheb', CompoundEntry.DB_CHEBI),
        ('name', 'names'),
    )


class CompoundName(VocabularyModel):
    max_length = 128
    abundance_accessor = 'compoundentry__abundance'


class FunctionName(VocabularyModel):
    max_length = 128
    abundance_accessor = 'funcrefdbentry__abundance'


class Location(VocabularyModel):
    class Meta(Model.Meta):
        verbose_name = 'subcellular location'


class Metal(VocabularyModel):
    pass


class ReactionEntryManager(Manager):
    def create_from_m2m_input(self, values, source_model, src_field_name):
        if source_model is not UniRef100:
            raise NotImplementedError(
                'can only create instance on behalf of UniRef100'
            )
        if src_field_name == 'kegg_reactions':
            db = self.model.DB_KEGG
        elif src_field_name == 'rhea_reactions':
            db = self.model.DB_RHEA
        elif src_field_name == 'biocyc_reactions':
            db = self.model.DB_BIOCYC
        else:
            raise ValueError(f'unknown source field name: {src_field_name}')

        # create one unique reaction group per value
        try:
            last_pk = Reaction.objects.order_by('pk').latest('pk').pk
        except Reaction.DoesNotExist:
            last_pk = -1
        Reaction.objects.bulk_create(
            (Reaction() for _ in range(len(values))),
            batch_size=500,  # runs up at SQLITE_MAX_COMPOUND_SELECT
        )
        reaction_pks = Reaction.objects.filter(pk__gt=last_pk)\
                               .values_list('pk', flat=True)
        if len(values) != len(reaction_pks):
            # just checking
            raise RuntimeError('a bug making right number of Reaction objects')

        model = self.model
        objs = (model(accession=i, db=db, reaction_id=j)
                for i, j in zip(values, reaction_pks))
        return self.bulk_create(objs)


class ReactionEntry(Model):
    DB_BIOCYC = 'b'
    DB_KEGG = 'k'
    DB_RHEA = 'r'
    DB_CHOICES = (
        (DB_BIOCYC, 'Biocyc'),
        (DB_KEGG, 'KEGG'),
        (DB_RHEA, 'RHEA'),
    )

    accession = AccessionField()
    db = models.CharField(max_length=1, choices=DB_CHOICES, db_index=True)
    bi_directional = models.BooleanField(blank=True, null=True)
    left = models.ManyToManyField(
        CompoundEntry, related_name='to_reaction',
    )
    right = models.ManyToManyField(
        CompoundEntry, related_name='from_reaction',
    )
    reaction = models.ForeignKey('Reaction', **fk_req)

    objects = ReactionEntryManager()

    def __str__(self):
        return self.accession


class Reaction(Model):
    """ distinct DB-independent reaction """

    # no fields here!

    loader_spec = CSV_Spec(
        ('ID', 'accession'),
        ('dir', 'dir'),
        ('left_kegg', 'left_kegg'),
        ('left_biocyc', 'left_biocyc'),
        ('left_rhea', 'left_rhea'),
        ('right_kegg', 'right_kegg'),
        ('right_biocyc', 'right_biocyc'),
        ('right_rhea', 'right_rhea'),
        ('kegg_rxn', ReactionEntry.DB_KEGG),
        ('biocyc_rxn', ReactionEntry.DB_BIOCYC),
        ('rhea_rxn', ReactionEntry.DB_RHEA),
    )

    loader = manager.ReactionLoader()

    class Meta:
        verbose_name = 'distinct reaction'


class FuncRefDBEntry(Model):
    DB_COG = 'cog'
    DB_EC = 'ec'
    DB_GO = 'go'
    DB_IPR = 'ipr'
    DB_PFAM = 'pfam'
    DB_TCDB = 'tcdb'
    DB_TIGR = 'tigr'
    DB_CHOICES = (
        (DB_COG, 'COG'),
        (DB_EC, 'EC'),
        (DB_GO, 'GO'),
        (DB_IPR, 'InterPro'),
        (DB_PFAM, 'Pfam'),
        (DB_TCDB, 'TCDB'),
        (DB_TIGR, 'TIGR'),
    )
    accession = AccessionField()
    db = models.CharField(max_length=4, choices=DB_CHOICES, db_index=True)
    names = models.ManyToManyField('FunctionName')

    loader = manager.FuncRefDBEntryLoader()

    class Meta(Model.Meta):
        verbose_name = 'Function Ref DB Entry'
        verbose_name_plural = 'Func Ref DB Entries'

    def __str__(self):
        return self.accession

    external_urls = {
        DB_COG: 'https://www.ncbi.nlm.nih.gov/research/cog/cog/{}/',
        DB_EC: '',
        DB_GO: 'http://amigo.geneontology.org/amigo/term/{}',
        DB_IPR: 'https://www.ebi.ac.uk/interpro/entry/InterPro/{}/',
        DB_PFAM: 'https://pfam.xfam.org/family/{}',
        DB_TCDB: '',
        DB_TIGR: '',
    }

    def get_external_url(self):
        url_spec = self.external_urls.get(self.db, None)
        if not url_spec:
            return None
        elif isinstance(url_spec, str):
            # assume simple formatting string
            return url_spec.format(self.accession)
        else:
            # assumme a tuple (templ, func)
            return url_spec[0].format(url_spec[1](self.accession))


class TaxName(Model):

    RANKS = (
        (0, 'root'),
        (1, 'domain'),
        (2, 'phylum'),
        (3, 'klass'),
        (4, 'order'),
        (5, 'family'),
        (6, 'genus'),
        (7, 'species'),
        (8, 'strain'),
    )
    RANK_CHOICE = ((i[0], i[1]) for i in RANKS)

    rank = models.PositiveSmallIntegerField(choices=RANK_CHOICE)
    name = models.CharField(max_length=64, db_index=True)

    loader = manager.TaxNameLoader()

    class Meta(Model.Meta):
        unique_together = (('rank', 'name'),)
        verbose_name = 'taxonomic name'

    def __str__(self):
        return f'{self.get_rank_display()} {self.name}'

    @classmethod
    def get_search_field(cls):
        return cls._meta.get_field('name')


class Lineage(Model):
    """
    Models taxonomic lineages

    TaxName fields must be declared in order of ranks from highest to lowest.
    """
    domain = models.ForeignKey(
        TaxName, **fk_opt,
        related_name='tax_dom_rel',
    )
    phylum = models.ForeignKey(
        TaxName, **fk_opt,
        related_name='tax_phy_rel',
    )
    klass = models.ForeignKey(
        TaxName, **fk_opt,
        related_name='tax_cls_rel',
        verbose_name='class',
    )
    order = models.ForeignKey(
        TaxName, **fk_opt,
        related_name='tax_ord_rel',
    )
    family = models.ForeignKey(
        TaxName, **fk_opt,
        related_name='tax_fam_rel',
    )
    genus = models.ForeignKey(
        TaxName, **fk_opt,
        related_name='tax_gen_rel',
    )
    species = models.ForeignKey(
        TaxName, **fk_opt,
        related_name='tax_sp_rel',
    )
    strain = models.ForeignKey(
        TaxName, **fk_opt,
        related_name='tax_str_rel',
    )

    loader = manager.LineageLoader()

    class Meta(Model.Meta):
        unique_together = (
            ('domain', 'phylum', 'klass', 'order', 'family', 'genus',
             'species', 'strain'),
        )

    def __str__(self):
        return f'{self.lineage}'

    @classmethod
    def get_name_fields(cls):
        """Return list of tax name fields in order"""
        return [
            i for i in cls._meta.get_fields()
            if i.many_to_one and i.related_model is TaxName
        ]

    @classmethod
    def get_parse_and_lookup_fun(cls):
        """
        Returns a funtion that parses a lineage str and returns the object

        More precisely, the return value is a tuple (lineage, key) where
        exactly one value is None, depending on the outcome.  If a lineage is
        found, key is None, if no lineage is found (returning None for it),
        then the key returned is a tuple of TaxName PKs, representing the
        missing lineage.
        """
        rank2key = {j: i for i, j in TaxName.RANKS}
        rankkeys = [rank2key[i.name] for i in cls.get_name_fields()]  # 1..8
        name2pk = {
            (name, rank): pk
            for name, rank, pk
            in TaxName.objects.values_list('name', 'rank', 'pk').iterator()
        }
        key2obj = {i.get_name_pks(): i for i in cls.objects.all().iterator()}

        def parse_and_lookup(value):
            """
            Get lineage object from string value

            :param str value:
                A string lineage, e.g. 'BACTERIA;BACTEROIDETES;FLAVOBACTERIIA'

            Returns a tuple (obj, missing_key), where obj is a Lineage instance
            and missing_key is None if a lineage corresponing to the passed
            value exists.  If no such lineage is in the database, then obj is
            None and missing_key contains the name-PK-key corresponding to the
            given lineage string.

            Raises TaxName.DoesNotExist if the given lineage string contains an
            unknown tax name.
            """
            try:
                key = tuple((
                    None if i is None else name2pk[(i, j)]
                    for i, j in zip_longest(value.split(';'), rankkeys)
                ))
            except KeyError as e:
                # e.args[0] should be (name, rankid)
                raise TaxName.DoesNotExist(e.args[0]) from e
            try:
                return key2obj[key], None
            except KeyError:
                return None, key

        return parse_and_lookup

    def get_name_pks(self):
        """
        Return tuple of all names' PK (incl. Nones)
        """
        return tuple((
            getattr(self, i.name + '_id')
            for i in self.get_name_fields()
        ))

    @classmethod
    def from_name_pks(cls, name_pks):
        """
        Return a new instance from list of TaxName PKs

        The instance is not saved on the database.
        """
        obj = cls()
        for field, pk in zip_longest(cls.get_name_fields(), name_pks):
            setattr(obj, field.name + '_id', pk)
        return obj

    def as_list_of_tuples(self):
        """
        Return instance as list of (rank, name) tuples
        """
        ret = []
        for i in self.get_name_fields():
            name = getattr(self, i.name, None)
            if name is None:
                continue
            ret.append((i.name, name))
        return ret

    lineage_list = cached_property(as_list_of_tuples, name='lineage_list')

    def names(self, with_missing_ranks=True):
        """ return dict of taxnames """
        names = OrderedDict()
        for i in TaxName.RANKS[1:]:
            attr = i[-1]
            name = getattr(self, attr, None)
            if name is None and not with_missing_ranks:
                break
            else:
                names[attr] = name

        return names

    @classmethod
    def format_lineage(cls, lineage, sep=';'):
        """
        Format a list of str taxnames as lineage
        """
        return sep.join(lineage)

    @property
    def lineage(self):
        return self.format_lineage((i.name for _, i in self.lineage_list))

    @classmethod
    def lca_lineage(cls, taxa):
        """
        Return lineage of LCA of given taxa

        Arguments:
            taxa: Taxon queryset or iterable of taxids or Taxon instances
        """
        if not taxa:
            raise ValueError(
                'taxa should be a list or iterable with at least one element'
            )
        # ranks are rank field attr names str from 'domain' to 'strain'
        ranks = [j[-1] for j in TaxName.RANKS[1:]]

        # lca: a list of tuples (rank_name, taxname_id)
        lca = None
        for i in taxa:
            if isinstance(i, int):
                obj = cls.objects(taxid=i)
            else:
                obj = i

            if lca is None:
                # init lca
                lca = []
                for r in ranks:
                    rid = getattr(obj, r + '_id', None)
                    if rid is None:
                        break
                    lca.append((r, rid))
                continue

            # calc new lca
            new_lca = []
            for r, rid in lca:
                if rid == getattr(obj, r + '_id', None):
                    new_lca.append((r, rid))
                    continue
                else:
                    break
            lca = new_lca

        # retrieve names
        qs = TaxName.objects.filter(pk__in=[i[1] for i in lca])
        names = dict(qs.values_list('pk', 'name'))

        # return just the tax names
        return [names[i[1]] for i in lca]

    @classmethod
    def orphan(cls):
        rels = ['taxon', 'contigcluster', 'gene', 'uniref100']
        f = {i: None for i in rels}
        return cls.objects.filter(**f)


class Taxon(Model):
    taxid = models.PositiveIntegerField(
        unique=True, verbose_name='NCBI taxid',
    )
    lineage = models.ForeignKey(Lineage, **fk_opt)

    loader = manager.TaxonLoader()

    class Meta(Model.Meta):
        verbose_name_plural = 'taxa'

    def __str__(self):
        return f'{self.taxid} {self.lineage}'

    @classmethod
    def classified(cls, lineage):
        """ remove unclassified tail of a lineage """
        ranks = [i[1].upper() for i in cls.RANK_CHOICE[1:]]
        ret = lineage[:1]  # keep first
        for rank, name in zip(ranks, lineage[1:]):
            if name == f'UNCLASSIFIED_{ret[-1]}_{rank}':
                break
            ret.append(name)

        return ret


class Uniprot(Model):
    accession = AccessionField(verbose_name='uniprot id')

    class Meta(Model.Meta):
        verbose_name = 'Uniprot'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.accession

    def get_external_url(self):
        return f'https://www.uniprot.org/uniprot/{self.accession}'


class UniRef100(LoadMixin, Model):
    """
    Model for UniRef100 clusters
    """
    # The field comments below are based on the columns in
    # UNIREF100_INFO_DEC_2021.txt in order.

    #  1 UNIREF100
    accession = AccessionField(prefix='UNIREF100_')
    #  2 NAME
    function_names = models.ManyToManyField(FunctionName)
    #  3 LENGTH
    length = models.PositiveIntegerField(blank=True, null=True)
    #  4 UNIPROT_IDS
    uniprot = models.ManyToManyField(Uniprot)
    #  5 UNIREF90
    uniref90 = AccessionField(prefix='UNIREF90_', unique=False)
    #  6 TAXON_IDS
    taxa = models.ManyToManyField(Taxon)
    #  7 LINEAGE (method)
    lineage = models.ForeignKey(Lineage, **fk_req)
    #  8 SIGALPEP
    signal_peptide = models.CharField(max_length=32, **ch_opt)
    #  9 TMS
    tms = models.CharField(max_length=128, **ch_opt)
    # 10 DNA
    dna_binding = models.CharField(max_length=128, **ch_opt)
    # 11 METAL
    metal_binding = models.ManyToManyField(Metal)
    # 12 TCDB
    tcdb = models.CharField(max_length=128, **ch_opt)  # TODO: what is this?
    # 13 LOCATION
    subcellular_locations = models.ManyToManyField(Location)
    # 14-19 COG PFAM TIGR GO IPR EC
    function_refs = models.ManyToManyField(FuncRefDBEntry)
    # 20-22 KEGG RHEA BIOCYC
    kegg_reactions = models.ManyToManyField(
        ReactionEntry,
        related_name='uniref_kegg',
    )
    rhea_reactions = models.ManyToManyField(
        ReactionEntry,
        related_name='uniref_rhea',
    )
    biocyc_reactions = models.ManyToManyField(
        ReactionEntry,
        related_name='uniref_biocyc',
    )
    # 23 REACTANTS
    # 24 PRODUCTS
    # 25 TRANS_CPD
    trans_compounds = models.ManyToManyField(
        CompoundEntry,
        related_name='uniref_trans',
    )

    class Meta:
        verbose_name = 'UniRef100'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.accession

    import_file_spec = (
        ('UNIREF100', 'accession'),
        ('NAME', 'function_names'),
        ('LENGTH', 'length'),
        ('UNIPROT_IDS', 'uniprot'),
        ('UNIREF90', 'uniref90'),
        ('TAXON_IDS', 'taxa'),
        ('LINEAGE', 'lineage'),
        ('SIGALPEP', 'signal_peptide'),
        ('TMS', 'tms'),
        ('DNA', 'dna_binding'),
        ('METAL', 'metal_binding'),
        ('TCDB', 'tcdb'),
        ('LOCATION', 'subcellular_locations'),
        ('COG', FuncRefDBEntry.DB_COG),
        ('PFAM', FuncRefDBEntry.DB_PFAM),
        ('TIGR', FuncRefDBEntry.DB_TIGR),
        ('GO', FuncRefDBEntry.DB_GO),
        ('IPR', FuncRefDBEntry.DB_IPR),
        ('EC', FuncRefDBEntry.DB_EC),
        ('KEGG', 'kegg_reactions',),
        ('RHEA', 'rhea_reactions'),
        ('BIOCYC', 'biocyc_reactions'),
        ('REACTANTS', None),
        ('PRODUCTS', None),
        ('TRANS_CPD', 'trans_compounds'),
    )

    @classmethod
    def get_file(cls):
        if 'UNIREF100_INFO_PATH' in dir(settings):
            return settings.UNIREF100_INFO_PATH
        else:
            # FIXME
            return (Path(settings.UMRAD_ROOT) / 'UNIPROT'
                    / 'UNIREF100_INFO_DEC_2021.txt')

    @classmethod
    @atomic
    def load(cls, max_rows=None, start=0, dry_run=False):
        # get data and split m2m fields
        refdb_keys = [i for i, _ in FuncRefDBEntry.DB_CHOICES]
        rxndb_keys = [i for i, _ in ReactionEntry.DB_CHOICES]
        field_names = [i.name for i in cls._meta.get_fields()]

        m2mcols = []
        for _, i in cls.import_file_spec:
            try:
                field = cls._meta.get_field(i)
            except FieldDoesNotExist:
                if i in refdb_keys or i in rxndb_keys:
                    m2mcols.append(i)
            else:
                if field.many_to_many:
                    m2mcols.append(i)
        del field

        # get lookups for FK PKs
        print('Retrieving lineage data... ', end='', flush=True)
        get_lineage = Lineage.get_parse_and_lookup_fun()
        print('[OK]')

        objs = []
        m2m_data = {}
        xref_data = defaultdict(list)  # maps a ref DB references to UniRef100s
        new_lineages = defaultdict(list)
        unknown_names = set()

        data = super().load(max_rows=max_rows, start=start, parse_only=True)
        for row in data:
            obj = cls()
            m2m = {}
            xrefs = []  # a list of pairs: (db, xref list)
            for key, value in row.items():

                if value == '':
                    continue

                if key in field_names:
                    if key in m2mcols:
                        # regular m2m fields
                        m2m[key] = value
                    elif key == 'lineage':
                        try:
                            lineage, name_pks = get_lineage(value)
                        except TaxName.DoesNotExist as e:
                            # unknown taxname encountered
                            unknown_names.add(e.args[0])
                            obj.lineage_id = 1  # quiddam FIXME
                        else:
                            if lineage is None:
                                # lineage not found in DB
                                # save with index so we find the obj later
                                new_lineages[name_pks].append(len(objs))
                            else:
                                obj.lineage = lineage
                    else:
                        # regular field (length, dna_binding, ...)
                        setattr(obj, key, value)
                elif key in m2mcols and key in refdb_keys:
                    # ref DB references
                    xrefs.append((key, cls._split_m2m_input(value)))
                else:
                    raise RuntimeError(
                        f'a bug, other cases were supposed to be'
                        f'exhaustive: {key=} {field_names=} {m2mcols=} '
                        f'{refdb_keys=}'
                    )

            acc = obj.get_accession_single()
            if acc in m2m_data:
                # duplicate row !!?!??
                print(f'WARNING: skipping row with duplicate UniRef100 '
                      f'accession: {acc}')
                continue

            m2m_data[acc] = m2m
            objs.append(obj)
            for dbkey, values in xrefs:
                for i in values:
                    xref_data[(i, dbkey)].append(acc)

        del row, key, value, values, xrefs, acc, dbkey

        if unknown_names:
            print(f'WARNING: {len(unknown_names)} unique unknown tax names:',
                  ' '.join([str(i) for i in islice(unknown_names, 5)]), '...')

        if new_lineages:
            # create+save+reload new lineages, then set missing PKs in unirefs
            try:
                maxpk = Lineage.objects.latest('pk').pk
            except Lineage.DoesNotExist:
                maxpk = 0
            Lineage.objects.bulk_create(
                (Lineage.from_name_pks(i) for i in new_lineages.keys())
            )
            for i in Lineage.objects.filter(pk__gt=maxpk):
                for j in new_lineages[i.get_name_pks()]:
                    objs[j].lineage_id = i.pk  # set lineage PK to UniRef obj
            del maxpk

        m2m_fields = list(m2m.keys())
        del m2m

        cls.objects.bulk_create(objs)

        # get accession -> pk map
        acc2pk = dict(
            cls.objects
            .values_list(cls.get_accession_lookup_single(), 'pk')
            .iterator()
        )

        # replace accession with pk in m2m data keys
        m2m_data = {acc2pk[i]: data for i, data in m2m_data.items()}

        # collecting all m2m entries
        for i in m2m_fields:
            cls._update_m2m(i, m2m_data)
        del m2m_data

        # store new xref entries
        existing_xrefs = set(
            FuncRefDBEntry.objects
            .values_list('accession', flat=True)
            .iterator()
        )
        xref_objs = (FuncRefDBEntry(accession=i, db=db)
                     for (i, db) in xref_data.keys()
                     if i not in existing_xrefs)
        FuncRefDBEntry.objects.bulk_create(xref_objs)
        del existing_xrefs

        # get PKs for xref objects
        xref2pk = dict(
            FuncRefDBEntry.objects.values_list('accession', 'pk').iterator()
        )

        # store UniRef100 <-> FuncRefDBEntry relations
        rels = (
            (acc2pk[i], xref2pk[xref])
            for (xref, _), accs in xref_data.items()
            for i in accs
        )
        through = cls._meta.get_field('function_refs').remote_field.through
        through_objs = (
            through(uniref100_id=i, funcrefdbentry_id=j)
            for i, j in rels
        )
        through_objs = list(through_objs)
        Manager.bulk_create_wrapper(through.objects.bulk_create)(through_objs)

        set_rollback(dry_run)

    def get_external_url(self):
        return f'https://www.uniprot.org/uniref/{self.accession}'


# development stuff
def delete_all_uniref100_etc():
    r = get_registry()
    for i in r.apps['mibios_umrad'].get_models():
        if i._meta.model_name.startswith('tax'):
            continue
        print(f'Deleting: {i} ', end='', flush=True)
        delete_all_objects_quickly(i)
        print('[done]')
