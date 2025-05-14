from modeltranslation.translator import register, TranslationOptions
from .models import Direction, Criterion, Team # Team.name ни ҳам таржима қилиш мумкин

@register(Direction)
class DirectionTranslationOptions(TranslationOptions):
    fields = ('name', 'description') # Таржима қилинадиган майдонлар

@register(Criterion)
class CriterionTranslationOptions(TranslationOptions):
    fields = ('name', 'description')

# Агар Team.name ҳам таржима қилинадиган бўлса:
# @register(Team)
# class TeamTranslationOptions(TranslationOptions):
#     fields = ('name',)