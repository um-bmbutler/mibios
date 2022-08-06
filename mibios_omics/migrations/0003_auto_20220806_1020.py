# Generated by Django 2.2.26 on 2022-08-06 14:20

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('mibios_omics', '0002_auto_20220628_1415'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='sample',
            name='accession',
        ),
        migrations.AddField(
            model_name='sample',
            name='analysis_dir',
            field=models.CharField(blank=True, default=None, help_text='path to results of analysis, relative to OMICS_DATA_ROOT', max_length=256, null=True),
        ),
        migrations.AddField(
            model_name='sample',
            name='sample_id',
            field=models.CharField(default='foo', help_text='sample ID given by study', max_length=256),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='sample',
            name='sample_type',
            field=models.CharField(blank=True, default=None, max_length=32, null=True),
        ),
        migrations.AddField(
            model_name='sample',
            name='tracking_id',
            field=models.CharField(blank=True, default=None, help_text='internal uniform hex id', max_length=32, null=True, unique=True),
        ),
        migrations.AddField(
            model_name='samplegroup',
            name='short_name',
            field=models.CharField(default='foo', help_text='a short name or description, for internal use, not (necessarily) for public display', max_length=64, unique=True),
            preserve_default=False,
        ),
    ]
