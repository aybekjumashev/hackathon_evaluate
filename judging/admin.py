from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin # User учун керак
from django.contrib.auth.models import User # User учун керак
from .models import Team, Criterion, Evaluation, Direction, JudgeProfile # Direction ва JudgeProfile импорт қилинганлигига ишонч ҳосил қилинг
from django.utils.translation import gettext_lazy as _

@admin.register(Direction) # <--- МАНА ШУ ҚИСМ ЙЎНАЛИШЛАР УЧУН
class DirectionAdmin(admin.ModelAdmin):
    list_display = ('name', 'description') # Админкада кўринадиган устунлар
    search_fields = ('name',)             # Номи бўйича қидириш
    # list_editable = ('description',)    # Агар тавсифни рўйхатдаёқ ўзгартирмоқчи бўлсангиз

@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ('name', 'direction')
    list_filter = ('direction',)
    search_fields = ('name', 'direction__name')
    autocomplete_fields = ['direction'] # Бу DirectionAdmin рўйхатдан ўтгандан кейин ишлайди

# JudgeProfile'ни User админкасига inline қилиб қўшиш
class JudgeProfileInline(admin.StackedInline): 
    model = JudgeProfile
    can_delete = False
    verbose_name_plural = _('Ҳакам профили (Йўналиш)')
    autocomplete_fields = ['assigned_direction'] # Бу ҳам DirectionAdmin рўйхатдан ўтгандан кейин ишлайди

# User админкасини қайта рўйхатдан ўтказиш
class UserAdmin(BaseUserAdmin):
    inlines = (JudgeProfileInline,)

# Агар UserAdmin аввалроқ рўйхатдан ўтган бўлса, уни ўчириб, янгисини қўшамиз
# Бу блок фақат бир марта ишлаши керак, ёки код бошида бўлса хавфсизроқ
try:
    admin.site.unregister(User) # Аввалги User админкасини ўчириш
    admin.site.register(User, UserAdmin) # Янгисини JudgeProfile билан рўйхатдан ўтказиш
except admin.sites.NotRegistered: # Агар User ҳали рўйхатдан ўтмаган бўлса (камдан-кам ҳолат)
    admin.site.register(User, UserAdmin)


@admin.register(Criterion)
class CriterionAdmin(admin.ModelAdmin):
    list_display = ('order', 'name', 'max_score')
    list_editable = ('max_score',)
    ordering = ('order',)

@admin.register(Evaluation)
class EvaluationAdmin(admin.ModelAdmin):
    list_display = ('team', 'criterion', 'judge', 'score', 'status', 'timestamp', 'last_updated')
    list_filter = ('judge', 'team', 'criterion', 'status')
    search_fields = ('team__name', 'criterion__name', 'judge__username')
    list_editable = ('score', 'status')
    readonly_fields = ('timestamp', 'last_updated')