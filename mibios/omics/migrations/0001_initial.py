# Generated by Django 3.2.16 on 2022-11-17 16:38

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.db.models.manager
import mibios.models
import mibios.omics.fields
import mibios.umrad.fields


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('umrad', '0001_initial'),
        migrations.swappable_dependency(settings.OMICS_DATASET_MODEL),
        migrations.swappable_dependency(settings.OMICS_SAMPLE_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Dataset',
            fields=[
                ('id', mibios.models.AutoField(primary_key=True, serialize=False)),
                ('dataset_id', models.PositiveIntegerField(help_text='internal accession to data set/study/project', unique=True)),
                ('short_name', models.CharField(blank=True, default=None, help_text='a short name or description, for internal use, not (necessarily) for public display', max_length=64, null=True, unique=True)),
            ],
            options={
                'swappable': 'OMICS_DATASET_MODEL',
            },
        ),
        migrations.CreateModel(
            name='Alignment',
            fields=[
                ('id', mibios.models.AutoField(primary_key=True, serialize=False)),
                ('score', models.PositiveIntegerField()),
            ],
            managers=[
                ('loader', django.db.models.manager.Manager()),
            ],
        ),
        migrations.CreateModel(
            name='BinMAX',
            fields=[
                ('id', mibios.models.AutoField(primary_key=True, serialize=False)),
                ('number', models.PositiveIntegerField()),
            ],
            options={
                'verbose_name': 'MaxBin',
                'verbose_name_plural': 'MaxBin bins',
            },
        ),
        migrations.CreateModel(
            name='BinMET93',
            fields=[
                ('id', mibios.models.AutoField(primary_key=True, serialize=False)),
                ('number', models.PositiveIntegerField()),
            ],
            options={
                'verbose_name': 'MetaBin 97/93',
                'verbose_name_plural': 'MetaBin 97/93 bins',
            },
        ),
        migrations.CreateModel(
            name='BinMET97',
            fields=[
                ('id', mibios.models.AutoField(primary_key=True, serialize=False)),
                ('number', models.PositiveIntegerField()),
            ],
            options={
                'verbose_name': 'MetaBin 99/97',
                'verbose_name_plural': 'MetaBin 99/97 bins',
            },
        ),
        migrations.CreateModel(
            name='BinMET99',
            fields=[
                ('id', mibios.models.AutoField(primary_key=True, serialize=False)),
                ('number', models.PositiveIntegerField()),
            ],
            options={
                'verbose_name': 'MetaBin 99/99',
                'verbose_name_plural': 'MetaBin 99/99 bins',
            },
        ),
        migrations.CreateModel(
            name='CheckM',
            fields=[
                ('id', mibios.models.AutoField(primary_key=True, serialize=False)),
                ('translation_table', models.PositiveSmallIntegerField(verbose_name='Translation table')),
                ('gc_std', models.FloatField(verbose_name='GC std')),
                ('ambiguous_bases', models.PositiveIntegerField(verbose_name='# ambiguous bases')),
                ('genome_size', models.PositiveIntegerField(verbose_name='Genome size')),
                ('longest_contig', models.PositiveIntegerField(verbose_name='Longest contig')),
                ('n50_scaffolds', models.PositiveIntegerField(verbose_name='N50 (scaffolds)')),
                ('mean_scaffold_len', models.FloatField(verbose_name='Mean scaffold length')),
                ('num_contigs', models.PositiveIntegerField(verbose_name='# contigs')),
                ('num_scaffolds', models.PositiveIntegerField(verbose_name='# scaffolds')),
                ('num_predicted_genes', models.PositiveIntegerField(verbose_name='# predicted genes')),
                ('longest_scaffold', models.PositiveIntegerField(verbose_name='Longest scaffold')),
                ('gc', models.FloatField(verbose_name='GC')),
                ('n50_contigs', models.PositiveIntegerField(verbose_name='N50 (contigs)')),
                ('coding_density', models.FloatField(verbose_name='Coding density')),
                ('mean_contig_length', models.FloatField(verbose_name='Mean contig length')),
            ],
            options={
                'verbose_name': 'CheckM',
                'verbose_name_plural': 'CheckM records',
            },
        ),
        migrations.CreateModel(
            name='Contig',
            fields=[
                ('id', mibios.models.AutoField(primary_key=True, serialize=False)),
                ('fasta_offset', models.PositiveIntegerField(blank=True, default=None, help_text='offset of first byte of fasta (or similar) header, if there is one, otherwise first byte of sequence', null=True)),
                ('fasta_len', models.PositiveIntegerField(blank=True, default=None, help_text='length of sequence record in bytes, header+sequence including internal and final newlines or until EOF.', null=True)),
                ('length', models.PositiveIntegerField(blank=True, default=None, null=True)),
                ('bases', models.PositiveIntegerField(blank=True, default=None, null=True)),
                ('coverage', models.DecimalField(blank=True, decimal_places=4, default=None, max_digits=10, null=True)),
                ('reads_mapped', models.PositiveIntegerField(blank=True, default=None, null=True)),
                ('rpkm_bbmap', models.DecimalField(blank=True, decimal_places=4, default=None, max_digits=10, null=True)),
                ('rpkm', models.FloatField(blank=True, default=None, null=True)),
                ('frags_mapped', models.PositiveIntegerField(blank=True, default=None, null=True)),
                ('fpkm_bbmap', models.DecimalField(blank=True, decimal_places=4, default=None, max_digits=10, null=True)),
                ('fpkm', models.FloatField(blank=True, default=None, null=True)),
                ('contig_id', mibios.umrad.fields.AccessionField(max_length=10, unique=False)),
                ('bin_m93', models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='members', to='omics.binmet93')),
                ('bin_m97', models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='members', to='omics.binmet97')),
                ('bin_m99', models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='members', to='omics.binmet99')),
                ('bin_max', models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='members', to='omics.binmax')),
                ('lca', models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.SET_NULL, to='umrad.taxon')),
                ('sample', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.OMICS_SAMPLE_MODEL)),
                ('taxid', models.ManyToManyField(related_name='classified_contig', to='umrad.TaxID')),
            ],
            options={
                'default_manager_name': 'objects',
                'unique_together': {('sample', 'contig_id')},
            },
        ),
        migrations.CreateModel(
            name='Gene',
            fields=[
                ('id', mibios.models.AutoField(primary_key=True, serialize=False)),
                ('fasta_offset', models.PositiveIntegerField(blank=True, default=None, help_text='offset of first byte of fasta (or similar) header, if there is one, otherwise first byte of sequence', null=True)),
                ('fasta_len', models.PositiveIntegerField(blank=True, default=None, help_text='length of sequence record in bytes, header+sequence including internal and final newlines or until EOF.', null=True)),
                ('length', models.PositiveIntegerField(blank=True, default=None, null=True)),
                ('bases', models.PositiveIntegerField(blank=True, default=None, null=True)),
                ('coverage', models.DecimalField(blank=True, decimal_places=4, default=None, max_digits=10, null=True)),
                ('reads_mapped', models.PositiveIntegerField(blank=True, default=None, null=True)),
                ('rpkm_bbmap', models.DecimalField(blank=True, decimal_places=4, default=None, max_digits=10, null=True)),
                ('rpkm', models.FloatField(blank=True, default=None, null=True)),
                ('frags_mapped', models.PositiveIntegerField(blank=True, default=None, null=True)),
                ('fpkm_bbmap', models.DecimalField(blank=True, decimal_places=4, default=None, max_digits=10, null=True)),
                ('fpkm', models.FloatField(blank=True, default=None, null=True)),
                ('gene_id', mibios.umrad.fields.AccessionField(max_length=20, unique=False)),
                ('start', models.PositiveIntegerField()),
                ('end', models.PositiveIntegerField()),
                ('strand', models.CharField(choices=[('+', '+'), ('-', '-')], max_length=1)),
                ('besthit', models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='gene_best', to='umrad.uniref100')),
                ('contig', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='omics.contig')),
                ('hits', models.ManyToManyField(related_name='gene_hit', through='omics.Alignment', to='umrad.UniRef100')),
                ('lca', models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.SET_NULL, to='umrad.taxon')),
                ('sample', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.OMICS_SAMPLE_MODEL)),
                ('taxid', models.ManyToManyField(related_name='classified_gene', to='umrad.TaxID')),
            ],
            options={
                'default_manager_name': 'objects',
                'unique_together': {('sample', 'gene_id')},
            },
        ),
        migrations.CreateModel(
            name='RNACentralRep',
            fields=[
                ('id', mibios.models.AutoField(primary_key=True, serialize=False)),
            ],
            options={
                'abstract': False,
                'default_manager_name': 'objects',
            },
        ),
        migrations.CreateModel(
            name='RNACentral',
            fields=[
                ('id', mibios.models.AutoField(primary_key=True, serialize=False)),
                ('accession', mibios.umrad.fields.AccessionField()),
                ('rna_type', models.PositiveSmallIntegerField(choices=[(1, 'antisense_RNA'), (2, 'autocatalytically_spliced_intron'), (3, 'guide_RNA'), (4, 'hammerhead_ribozyme'), (5, 'lncRNA'), (6, 'miRNA'), (7, 'misc_RNA'), (8, 'ncRNA'), (9, 'other'), (10, 'piRNA'), (11, 'precursor_RNA'), (12, 'pre_miRNA'), (13, 'ribozyme'), (14, 'RNase_MRP_RNA'), (15, 'RNase_P_RNA'), (16, 'rRNA'), (17, 'scaRNA'), (18, 'scRNA'), (19, 'siRNA'), (20, 'snoRNA'), (21, 'snRNA'), (22, 'sRNA'), (23, 'SRP_RNA'), (24, 'telomerase_RNA'), (25, 'tmRNA'), (26, 'tRNA'), (27, 'vault_RNA'), (28, 'Y_RNA')])),
                ('taxon', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='umrad.taxon')),
            ],
            options={
                'abstract': False,
                'default_manager_name': 'objects',
            },
        ),
        migrations.CreateModel(
            name='ReadLibrary',
            fields=[
                ('id', mibios.models.AutoField(primary_key=True, serialize=False)),
                ('fwd_qc0_fastq', mibios.omics.fields.DataPathField(base='READS', default=None, max_length=1024, null=True)),
                ('rev_qc0_fastq', mibios.omics.fields.DataPathField(base='READS', default=None, max_length=1024, null=True)),
                ('fwd_qc1_fastq', mibios.omics.fields.DataPathField(base='READS', default=None, max_length=1024, null=True)),
                ('rev_qc1_fastq', mibios.omics.fields.DataPathField(base='READS', default=None, max_length=1024, null=True)),
                ('raw_read_count', models.PositiveIntegerField(blank=True, default=None, null=True)),
                ('qc_read_count', models.PositiveIntegerField(blank=True, default=None, null=True)),
                ('sample', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='reads', to=settings.OMICS_SAMPLE_MODEL)),
            ],
            options={
                'verbose_name_plural': 'read libraries',
            },
        ),
        migrations.CreateModel(
            name='Protein',
            fields=[
                ('id', mibios.models.AutoField(primary_key=True, serialize=False)),
                ('fasta_offset', models.PositiveIntegerField(blank=True, default=None, help_text='offset of first byte of fasta (or similar) header, if there is one, otherwise first byte of sequence', null=True)),
                ('fasta_len', models.PositiveIntegerField(blank=True, default=None, help_text='length of sequence record in bytes, header+sequence including internal and final newlines or until EOF.', null=True)),
                ('gene', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='omics.gene')),
                ('sample', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.OMICS_SAMPLE_MODEL)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.AddField(
            model_name='binmet99',
            name='checkm',
            field=models.OneToOneField(blank=True, default=None, null=True, on_delete=django.db.models.deletion.SET_NULL, to='omics.checkm'),
        ),
        migrations.AddField(
            model_name='binmet99',
            name='sample',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.OMICS_SAMPLE_MODEL),
        ),
        migrations.AddField(
            model_name='binmet97',
            name='checkm',
            field=models.OneToOneField(blank=True, default=None, null=True, on_delete=django.db.models.deletion.SET_NULL, to='omics.checkm'),
        ),
        migrations.AddField(
            model_name='binmet97',
            name='sample',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.OMICS_SAMPLE_MODEL),
        ),
        migrations.AddField(
            model_name='binmet93',
            name='checkm',
            field=models.OneToOneField(blank=True, default=None, null=True, on_delete=django.db.models.deletion.SET_NULL, to='omics.checkm'),
        ),
        migrations.AddField(
            model_name='binmet93',
            name='sample',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.OMICS_SAMPLE_MODEL),
        ),
        migrations.AddField(
            model_name='binmax',
            name='checkm',
            field=models.OneToOneField(blank=True, default=None, null=True, on_delete=django.db.models.deletion.SET_NULL, to='omics.checkm'),
        ),
        migrations.AddField(
            model_name='binmax',
            name='sample',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.OMICS_SAMPLE_MODEL),
        ),
        migrations.AddField(
            model_name='alignment',
            name='gene',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='omics.gene'),
        ),
        migrations.AddField(
            model_name='alignment',
            name='ref',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='umrad.uniref100'),
        ),
        migrations.CreateModel(
            name='Sample',
            fields=[
                ('id', mibios.models.AutoField(primary_key=True, serialize=False)),
                ('sample_id', models.CharField(blank=True, default=None, help_text='internal sample accession', max_length=256, null=True, unique=True)),
                ('tracking_id', models.CharField(blank=True, default=None, help_text='internal uniform hex id', max_length=32, null=True, unique=True)),
                ('sample_name', models.CharField(help_text='sample ID or name as given by study', max_length=64)),
                ('sample_type', models.CharField(blank=True, choices=[('amplicon', 'amplicon'), ('metagenome', 'metagenome'), ('metatranscriptome', 'metatranscriptome')], default=None, max_length=32, null=True)),
                ('has_paired_data', models.BooleanField(blank=True, default=None, null=True)),
                ('sra_accession', models.CharField(blank=True, default='', help_text='SRA accession', max_length=16)),
                ('amplicon_target', models.CharField(blank=True, default='', max_length=16)),
                ('fwd_primer', models.CharField(blank=True, default='', max_length=32)),
                ('rev_primer', models.CharField(blank=True, default='', max_length=32)),
                ('meta_data_loaded', models.BooleanField(default=False, help_text='meta data successfully loaded')),
                ('metag_pipeline_reg', models.BooleanField(default=False, help_text='is registered in metagenomic pipeline, has tracking ID')),
                ('contig_fasta_loaded', models.BooleanField(default=False, help_text='contig fasta data loaded')),
                ('gene_fasta_loaded', models.BooleanField(default=False, help_text='gene fasta data loaded')),
                ('contig_abundance_loaded', models.BooleanField(default=False, help_text='contig abundance/rpkm data data loaded')),
                ('gene_abundance_loaded', models.BooleanField(default=False, help_text='gene abundance/rpkm data loaded')),
                ('gene_alignment_hits_loaded', models.BooleanField(default=False, help_text='gene alignment hits to UniRef100 loaded')),
                ('binning_ok', models.BooleanField(default=False, help_text='Binning data loaded')),
                ('checkm_ok', models.BooleanField(default=False, help_text='Binning stats loaded')),
                ('genes_ok', models.BooleanField(default=False, help_text='Gene data and coverage loaded')),
                ('proteins_ok', models.BooleanField(default=False, help_text='Protein data loaded')),
                ('tax_abund_ok', models.BooleanField(default=False, help_text='Taxon abundance data loaded')),
                ('func_abund_ok', models.BooleanField(default=False, help_text='Function abundance data loaded')),
                ('comp_abund_ok', models.BooleanField(default=False, help_text='Compound abundance data loaded')),
                ('analysis_dir', models.CharField(blank=True, default=None, help_text='path to results of analysis, relative to OMICS_DATA_ROOT', max_length=256, null=True)),
                ('read_count', models.PositiveIntegerField(blank=True, default=None, help_text='number of read pairs (post-QC) used for assembly mapping', null=True)),
                ('reads_mapped_contigs', models.PositiveIntegerField(blank=True, default=None, help_text='number of reads mapped to contigs', null=True)),
                ('reads_mapped_genes', models.PositiveIntegerField(blank=True, default=None, help_text='number of reads mapped to genes', null=True)),
                ('dataset', models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.OMICS_DATASET_MODEL)),
            ],
            options={
                'swappable': 'OMICS_SAMPLE_MODEL',
            },
        ),
        migrations.CreateModel(
            name='TaxonAbundance',
            fields=[
                ('id', mibios.models.AutoField(primary_key=True, serialize=False)),
                ('sum_gene_rpkm', models.DecimalField(decimal_places=4, max_digits=12)),
                ('sample', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.OMICS_SAMPLE_MODEL)),
                ('taxon', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='abundance', to='umrad.taxon')),
            ],
            options={
                'abstract': False,
                'default_manager_name': 'objects',
                'unique_together': {('sample', 'taxon')},
            },
        ),
        migrations.CreateModel(
            name='NCRNA',
            fields=[
                ('id', mibios.models.AutoField(primary_key=True, serialize=False)),
                ('part', models.PositiveIntegerField(blank=True, default=None, null=True)),
                ('flag', models.PositiveIntegerField(help_text='bitwise FLAG')),
                ('pos', models.PositiveIntegerField(help_text='1-based leftmost mapping position')),
                ('mapq', models.PositiveIntegerField(help_text='MAPing Quality')),
                ('contig', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='omics.contig')),
                ('match', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='omics.rnacentralrep')),
                ('sample', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.OMICS_SAMPLE_MODEL)),
            ],
            options={
                'unique_together': {('sample', 'contig', 'part')},
            },
        ),
        migrations.CreateModel(
            name='FuncAbundance',
            fields=[
                ('id', mibios.models.AutoField(primary_key=True, serialize=False)),
                ('scos', models.DecimalField(decimal_places=2, max_digits=12)),
                ('rpkm', models.DecimalField(decimal_places=2, max_digits=12)),
                ('function', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='abundance', to='umrad.funcrefdbentry')),
                ('sample', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.OMICS_SAMPLE_MODEL)),
            ],
            options={
                'abstract': False,
                'default_manager_name': 'objects',
                'unique_together': {('sample', 'function')},
            },
        ),
        migrations.CreateModel(
            name='CompoundAbundance',
            fields=[
                ('id', mibios.models.AutoField(primary_key=True, serialize=False)),
                ('scos', models.DecimalField(decimal_places=2, max_digits=12)),
                ('rpkm', models.DecimalField(decimal_places=2, max_digits=12)),
                ('role', models.CharField(choices=[('r', 'REACTANT'), ('p', 'PRODUCT'), ('t', 'TRANSPORT')], max_length=1)),
                ('compound', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='abundance', to='umrad.compoundrecord')),
                ('sample', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.OMICS_SAMPLE_MODEL)),
            ],
            options={
                'abstract': False,
                'default_manager_name': 'objects',
                'unique_together': {('sample', 'compound', 'role')},
            },
        ),
        migrations.AlterUniqueTogether(
            name='alignment',
            unique_together={('gene', 'ref')},
        ),
    ]