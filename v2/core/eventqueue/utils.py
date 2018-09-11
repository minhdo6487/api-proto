from core.user.models import UserProfile
ENGLISH = 'E'
def update_user_profile(sender, instance, created, **kwargs):
    if instance.question.package.referer_object == 'UserProfile':
        obj = instance.user.user_profile
    else:
        obj = instance.user.usersettings
    if obj:
        
        answer_en = instance.text if instance.text else (instance.choice.choice_en if instance.choice else '')
        answer_vi = instance.text if instance.text else (instance.choice.choice_vi if instance.choice else '')
        answer = answer_en if instance.user.usersettings and instance.user.usersettings.language == ENGLISH else answer_vi
        answer = True if answer_en == 'Yes' else (False if answer_en == 'No' else answer)
        setattr(obj, instance.question.code_name, answer)
        if hasattr(obj, 'version'):
            setattr(obj, 'version', 2)
        obj.save()