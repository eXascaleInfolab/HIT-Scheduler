from django.contrib import admin
from accounts.models import Batch,Task

class TaskAdmin(admin.ModelAdmin):
    fieldsets = [
        (None,               {'fields': ['question','choice']}),
    ]
class TaskInline(admin.StackedInline):
    model = Task
    extra = 3
class BatchAdmin(admin.ModelAdmin):
    fieldsets = [
        (None,     {'fields': ['value','repetition','numtask','bclass','name']}),
    ]
    def formfield_for_choice_field(self, db_field, request, **kwargs):
        if db_field.name == "bclass":
            kwargs['class'] = (('classify','classify'),('extract','extract'),('curate','curate'),('data','data'))
        return super(BatchAdmin, self).formfield_for_choice_field(db_field, request, **kwargs)
    inlines = [TaskInline]

admin.site.register(Batch, BatchAdmin)
