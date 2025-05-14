from django.db import models
from django.contrib.auth.models import User # Django'нинг стандарт фойдаланувчи модели
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.translation import gettext_lazy as _


class Direction(models.Model):
    name = models.CharField(max_length=200, unique=True, verbose_name=_("Йўналиш номи")) # Ўзгарди
    description = models.TextField(blank=True, null=True, verbose_name=_("Қисқача тавсиф")) # Ўзгарди

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _("Йўналиш") # Ўзгарди
        verbose_name_plural = _("Йўналишлар") # Ўзгарди
        ordering = ['name']

class Team(models.Model):
    name = models.CharField(max_length=200, unique=True, verbose_name=_("Жамоа номи"))
    direction = models.ForeignKey(
        Direction, 
        on_delete=models.PROTECT, # Агар йўналиш ўчирилса, жамоа йўналишсиз қолади (ёки models.PROTECT)
        verbose_name=_("Йўналиши")
    )
    
    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _("Жамоа")
        verbose_name_plural = _("Жамоалар")

class Criterion(models.Model):
    # T/P рақамига мос келиши учун
    order = models.PositiveIntegerField(unique=True, verbose_name=_("Тартиб рақами (T/P)"))
    name = models.CharField(max_length=255, verbose_name=_("Баҳолаш мезони"))
    max_score = models.IntegerField(verbose_name=_("Максимал балл"))
    description = models.TextField(verbose_name=_("Изоҳ (мезонни баҳолаш учун қўлланма)"), blank=True, null=True)
    # "Изоҳ"даги ҳар бир бандни алоҳида баҳолаш имконияти керак бўлса,
    # бу ерда SubCriterion моделига ForeignKey орқали боғланиш мумкин бўларди.
    # Ҳозирча соддароқ, изоҳ матн кўринишида сақланади.

    def __str__(self):
        return f"{self.order}. {self.name} (Макс: {self.max_score})"

    class Meta:
        verbose_name = _("Баҳолаш мезони")
        verbose_name_plural = _("Баҳолаш мезонлари")
        ordering = ['order']
        
class Evaluation(models.Model):
    STATUS_DRAFT = 'draft'
    STATUS_FINAL = 'final'
    STATUS_CHOICES = [
        (STATUS_DRAFT, 'Черновик'),
        (STATUS_FINAL, 'Қатъий'),
    ]

    judge = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name=_("Ҳакам"))
    team = models.ForeignKey(Team, on_delete=models.CASCADE, verbose_name=_("Жамоа"))
    criterion = models.ForeignKey(Criterion, on_delete=models.CASCADE, verbose_name=_("Мезон"))
    score = models.IntegerField(
        verbose_name=_("Берилган балл"),
        # Валидаторларни олиб ташлаб, save методига ишонамиз
    )
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default=STATUS_DRAFT,
        verbose_name=_("Ҳолати")
    )
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name=_("Баҳолаш вақти"))
    last_updated = models.DateTimeField(auto_now=True, verbose_name=_("Охирги янгиланиш")) # Қўшимча

    def save(self, *args, **kwargs):
        if self.score is not None: # score киритилган бўлсагина текширамиз
            if self.score > self.criterion.max_score:
                self.score = self.criterion.max_score
            if self.score < 0:
                self.score = 0
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.team.name} - {self.criterion.name}: {self.score} ({self.get_status_display()}) (Ҳакам: {self.judge.username})"

    class Meta:
        verbose_name = _("Баҳо")
        verbose_name_plural = _("Баҳолар")
        unique_together = ('judge', 'team', 'criterion')
        ordering = ['timestamp']



class JudgeProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='judge_profile', verbose_name=_("Ҳакам (Фойдаланувчи)"))
    # ManyToMany ўрнига ForeignKey
    assigned_direction = models.ForeignKey(
        Direction,
        on_delete=models.SET_NULL, # Агар йўналиш ўчирилса, ҳакам йўналишсиз қолади
        null=True,  # Йўналиш бириктирилиши шарт эмас (optional)
        blank=True, # Админкада бўш қолдиришга рухсат
        verbose_name=_("Масъул йўналиш (ихтиёрий)"),
        help_text=_("Агар йўналиш танланмаса, ҳакам барча йўналишлардаги жамоаларни баҳолай олади.")
    )

    def __str__(self):
        if self.assigned_direction:
            # self.assigned_direction.name (modeltranslation орқали) жорий тилдаги сатрни қайтаради
            # " йўналиши" қисмини gettext орқали оламиз, чунки у __str__ ичида дарҳол керак
            # Ёки бутун сатрни _() билан ўраб, format() ишлатамиз
            
            # 1-вариант: gettext билан
            # direction_name_str = str(self.assigned_direction.name) # Агар name ўзи lazy бўлса
            # direction_suffix = gettext(" йўналиши") 
            # return f"{self.user.username} ({direction_name_str}{direction_suffix})"

            # 2-вариант: _().format() билан (кўпроқ тавсия этилади)
            direction_display = str(self.assigned_direction.name) if self.assigned_direction else _("аниқланмаган")
            # Django User моделининг username майдони одатда таржима қилинмайди
            return _("%(user_username)s (%(direction_name)s йўналиши)") % {
                'user_username': self.user.username,
                'direction_name': direction_display
            }
        else:
            # Django User моделининг username майдони одатда таржима қилинмайди
            return _("%(user_username)s (Барча йўналишлар)") % {
                'user_username': self.user.username
            }

    class Meta:
        verbose_name = _("Ҳакам профили")
        verbose_name_plural = _("Ҳакам профиллари")