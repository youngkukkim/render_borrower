from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('submissions', '0008_remove_submission_net_income_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='submission',
            name='normalized_payload',
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text='ntpd extractor가 생성한 중첩 구조 데이터',
            ),
        ),
        migrations.AddField(
            model_name='submission',
            name='normalized_records',
            field=models.JSONField(
                blank=True,
                default=list,
                help_text='레이블 경로/값을 flat하게 담은 리스트',
            ),
        ),
    ]
