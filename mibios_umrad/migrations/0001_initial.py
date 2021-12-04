# Generated by Django 2.2.24 on 2021-12-04 01:50

from django.db import migrations, models
import django.db.models.deletion
import mibios.models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='TaxName',
            fields=[
                ('id', mibios.models.AutoField(primary_key=True, serialize=False)),
                ('rank', models.PositiveSmallIntegerField(choices=[(0, 'root'), (1, 'domain'), (2, 'phylum'), (3, 'class'), (4, 'order'), (5, 'family'), (6, 'genus'), (7, 'species'), (8, 'strain')])),
                ('name', models.CharField(max_length=64)),
            ],
            options={
                'unique_together': {('rank', 'name')},
            },
        ),
        migrations.CreateModel(
            name='Taxon',
            fields=[
                ('id', mibios.models.AutoField(primary_key=True, serialize=False)),
                ('taxid', models.PositiveIntegerField(unique=True)),
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
                'abstract': False,
            },
        ),
    ]
