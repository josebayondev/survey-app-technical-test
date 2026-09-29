from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("surveys", "0001_initial")]

    operations = [
        migrations.AddConstraint(
            model_name="response",
            constraint=models.UniqueConstraint(
                fields=("survey", "external_id"), name="unique_response_event"
            ),
        ),
    ]
