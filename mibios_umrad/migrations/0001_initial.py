# Generated by Django 2.2.24 on 2021-12-17 20:03

from django.db import migrations, models
import django.db.models.deletion
import mibios.models
import mibios_umrad.fields


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('mibios', '0016_importfile_note'),
    ]

    operations = [
        migrations.CreateModel(
            name='Biocyc',
            fields=[
                ('id', mibios.models.AutoField(primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=64, unique=True)),
            ],
            options={
                'verbose_name': 'BioCyc',
                'verbose_name_plural': 'BioCyc',
            },
        ),
        migrations.CreateModel(
            name='COG',
            fields=[
                ('id', mibios.models.AutoField(primary_key=True, serialize=False)),
                ('accession', mibios_umrad.fields.AccessionField(prefix='COG')),
            ],
            options={
                'verbose_name': 'COG',
                'verbose_name_plural': 'COGs',
            },
        ),
        migrations.CreateModel(
            name='Compound',
            fields=[
                ('id', mibios.models.AutoField(primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=32, unique=True)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='EC',
            fields=[
                ('id', mibios.models.AutoField(primary_key=True, serialize=False)),
                ('accession', mibios_umrad.fields.AccessionField()),
            ],
            options={
                'verbose_name': 'EC',
                'verbose_name_plural': 'EC',
            },
        ),
        migrations.CreateModel(
            name='Function',
            fields=[
                ('id', mibios.models.AutoField(primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=128, unique=True)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='GeneOntology',
            fields=[
                ('id', mibios.models.AutoField(primary_key=True, serialize=False)),
                ('accession', mibios_umrad.fields.AccessionField(prefix='GO:')),
            ],
            options={
                'verbose_name': 'GeneOntology',
                'verbose_name_plural': 'GeneOntology',
            },
        ),
        migrations.CreateModel(
            name='Interpro',
            fields=[
                ('id', mibios.models.AutoField(primary_key=True, serialize=False)),
                ('accession', mibios_umrad.fields.AccessionField(prefix='IPR')),
            ],
            options={
                'verbose_name': 'Interpro',
                'verbose_name_plural': 'Interpro',
            },
        ),
        migrations.CreateModel(
            name='KEGG',
            fields=[
                ('id', mibios.models.AutoField(primary_key=True, serialize=False)),
                ('accession', mibios_umrad.fields.AccessionField(prefix='R')),
            ],
            options={
                'verbose_name': 'KEGG',
                'verbose_name_plural': 'KEGG',
            },
        ),
        migrations.CreateModel(
            name='Location',
            fields=[
                ('id', mibios.models.AutoField(primary_key=True, serialize=False)),
                ('entry', models.CharField(max_length=64, unique=True)),
                ('history', models.ManyToManyField(to='mibios.ChangeRecord')),
            ],
            options={
                'verbose_name': 'subcellular location',
            },
        ),
        migrations.CreateModel(
            name='Metal',
            fields=[
                ('id', mibios.models.AutoField(primary_key=True, serialize=False)),
                ('entry', models.CharField(max_length=64, unique=True)),
                ('history', models.ManyToManyField(to='mibios.ChangeRecord')),
            ],
            options={
                'ordering': ['entry'],
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='PFAM',
            fields=[
                ('id', mibios.models.AutoField(primary_key=True, serialize=False)),
                ('accession', mibios_umrad.fields.AccessionField(prefix='PF')),
            ],
            options={
                'verbose_name': 'PFAM',
            },
        ),
        migrations.CreateModel(
            name='RHEA',
            fields=[
                ('id', mibios.models.AutoField(primary_key=True, serialize=False)),
                ('accession', mibios_umrad.fields.AccessionField()),
            ],
            options={
                'verbose_name': 'RHEA',
                'verbose_name_plural': 'RHEA',
            },
        ),
        migrations.CreateModel(
            name='TaxName',
            fields=[
                ('id', mibios.models.AutoField(primary_key=True, serialize=False)),
                ('rank', models.PositiveSmallIntegerField(choices=[(0, 'root'), (1, 'domain'), (2, 'phylum'), (3, 'class'), (4, 'order'), (5, 'family'), (6, 'genus'), (7, 'species'), (8, 'strain')])),
                ('name', models.CharField(max_length=64)),
            ],
            options={
                'verbose_name': 'taxonomic name',
                'unique_together': {('rank', 'name')},
            },
        ),
        migrations.CreateModel(
            name='Taxon',
            fields=[
                ('id', mibios.models.AutoField(primary_key=True, serialize=False)),
                ('taxid', models.PositiveIntegerField()),
                ('domain', models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='tax_dom_rel', to='mibios_umrad.TaxName')),
                ('family', models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='tax_fam_rel', to='mibios_umrad.TaxName')),
                ('genus', models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='tax_gen_rel', to='mibios_umrad.TaxName')),
                ('klass', models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='tax_cls_rel', to='mibios_umrad.TaxName')),
                ('order', models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='tax_ord_rel', to='mibios_umrad.TaxName')),
                ('phylum', models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='tax_phy_rel', to='mibios_umrad.TaxName')),
                ('species', models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='tax_sp_rel', to='mibios_umrad.TaxName')),
                ('strain', models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='tax_str_rel', to='mibios_umrad.TaxName')),
            ],
            options={
                'verbose_name_plural': 'taxa',
                'unique_together': {('taxid', 'domain', 'phylum', 'klass', 'order', 'family', 'genus', 'species', 'strain')},
            },
        ),
        migrations.CreateModel(
            name='TIGR',
            fields=[
                ('id', mibios.models.AutoField(primary_key=True, serialize=False)),
                ('accession', mibios_umrad.fields.AccessionField(prefix='TIGR')),
            ],
            options={
                'verbose_name': 'TIGR',
                'verbose_name_plural': 'TIGR',
            },
        ),
        migrations.CreateModel(
            name='Uniprot',
            fields=[
                ('id', mibios.models.AutoField(primary_key=True, serialize=False)),
                ('accession', mibios_umrad.fields.AccessionField(verbose_name='uniprot id')),
            ],
            options={
                'verbose_name': 'Uniprot',
                'verbose_name_plural': 'Uniprot',
            },
        ),
        migrations.CreateModel(
            name='UniRef100',
            fields=[
                ('id', mibios.models.AutoField(primary_key=True, serialize=False)),
                ('accession', mibios_umrad.fields.AccessionField(prefix='UNIREF100_')),
                ('length', models.PositiveIntegerField()),
                ('uniref90', mibios_umrad.fields.AccessionField(prefix='UNIREF90_', unique=False)),
                ('signal_peptide', models.CharField(blank=True, default='', max_length=32)),
                ('tms', models.CharField(blank=True, default='', max_length=128)),
                ('dna_binding', models.CharField(blank=True, default='', max_length=128)),
                ('tcdb', models.CharField(blank=True, default='', max_length=128)),
                ('biocyc', models.ManyToManyField(to='mibios_umrad.Biocyc')),
                ('cog_kog', models.ManyToManyField(to='mibios_umrad.COG')),
                ('ec', models.ManyToManyField(to='mibios_umrad.EC')),
                ('function', models.ManyToManyField(to='mibios_umrad.Function')),
                ('gene_ontology', models.ManyToManyField(to='mibios_umrad.GeneOntology')),
                ('interpro', models.ManyToManyField(to='mibios_umrad.Interpro')),
                ('kegg', models.ManyToManyField(to='mibios_umrad.KEGG')),
                ('metal_binding', models.ManyToManyField(to='mibios_umrad.Metal')),
                ('pfam', models.ManyToManyField(to='mibios_umrad.PFAM')),
                ('product', models.ManyToManyField(related_name='product_of', to='mibios_umrad.Compound')),
                ('reactant', models.ManyToManyField(related_name='reactant_of', to='mibios_umrad.Compound')),
                ('rhea', models.ManyToManyField(to='mibios_umrad.RHEA')),
                ('subcellular_location', models.ManyToManyField(to='mibios_umrad.Location')),
                ('taxon', models.ManyToManyField(to='mibios_umrad.Taxon')),
                ('tigr', models.ManyToManyField(to='mibios_umrad.TIGR')),
                ('trans_cpd', models.ManyToManyField(related_name='trans_of', to='mibios_umrad.Compound')),
                ('uniprot', models.ManyToManyField(to='mibios_umrad.Uniprot')),
            ],
            options={
                'verbose_name': 'UniRef100',
                'verbose_name_plural': 'UniRef100',
            },
        ),
    ]