# Generated by Django 2.2.24 on 2021-12-18 02:33

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('mibios_umrad', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='taxon',
            name='taxid',
            field=models.PositiveIntegerField(unique=True),
        ),
        migrations.AlterUniqueTogether(
            name='taxon',
            unique_together=set(),
        ),
    ]