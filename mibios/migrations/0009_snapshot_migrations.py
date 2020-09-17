# Generated by Django 2.2.14 on 2020-09-04 21:54

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('mibios', '0008_snapshot_filename_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='snapshot',
            name='migrations',
            field=models.CharField(default='', editable=False, help_text='json serializaton of the last migrations of each app', max_length=3000),
        ),
    ]