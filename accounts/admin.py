from django.contrib import admin
from accounts.models import Batch,Task, UserProfile, TaskSubmit

class TaskAdmin(admin.ModelAdmin):
    fieldsets = [
        (None,               {'fields': ['question','choice']}),
    ]
class TaskInline(admin.StackedInline):
    model = Task
    extra = 3
class BatchAdmin(admin.ModelAdmin):
    fieldsets = [
        (None,     {'fields': ['name','bclass','done','value','repetition','numtask']}),
    ]
    def formfield_for_choice_field(self, db_field, request, **kwargs):
        if db_field.name == "bclass":
            kwargs['class'] = (('classify','classify'),('extract','extract'),('curate','curate'),('data','data'),('study','study'))
        return super(BatchAdmin, self).formfield_for_choice_field(db_field, request, **kwargs)
    inlines = [TaskInline]

class UserProfileAdmin(admin.ModelAdmin):
    list_display=('user','credit','score')


class TaskSubmitAdmin(admin.ModelAdmin):
    list_display = ('user', 'task', 'elapsed', 'bonus')

admin.site.register(TaskSubmit, TaskSubmitAdmin)
admin.site.register(Batch, BatchAdmin)
admin.site.register(UserProfile, UserProfileAdmin)
