# Generated manually to assign trial plan to existing users

from django.db import migrations


def assign_trial_plan_to_existing_users(apps, schema_editor):
    """Assign trial plan to all existing users who don't have a plan"""
    User = apps.get_model('account', 'User')
    Plan = apps.get_model('account', 'Plan')
    
    try:
        trial_plan = Plan.objects.get(plan_key='trial')
        
        # Find all users without a plan
        users_without_plan = User.objects.filter(current_plan__isnull=True)
        
        # Assign trial plan to them
        for user in users_without_plan:
            user.current_plan = trial_plan
            user.save()
            
        print(f"Assigned trial plan to {users_without_plan.count()} existing users")
    except Plan.DoesNotExist:
        print("Trial plan not found. Please run populate_plans command first.")


class Migration(migrations.Migration):

    dependencies = [
        ('account', '0003_plan_alter_user_billing_requests_remaining_and_more'),
    ]

    operations = [
        migrations.RunPython(assign_trial_plan_to_existing_users),
    ]
