from django.contrib import admin
from django.contrib.admin import SimpleListFilter
from django.utils.translation import ugettext_lazy as _
from accounts.models import Batch,Task, UserProfile, TaskSubmit

class TaskAdmin(admin.ModelAdmin):
    list_display = ('id', 'question')

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

class UserProfileAdmin(admin.ModelAdmin):
    list_display=('user','credit','score')


class TaskSubmitAdmin(admin.ModelAdmin):
    list_display = ('user', 'task', 'elapsed', 'bonus')
    list_filter = ('user',)

admin.site.register(TaskSubmit, TaskSubmitAdmin)
admin.site.register(Batch, BatchAdmin)
admin.site.register(Task, TaskAdmin)
admin.site.register(UserProfile, UserProfileAdmin)
