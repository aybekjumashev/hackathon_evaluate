# judging/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Team, Criterion, Evaluation, JudgeProfile, Direction # JudgeProfile ва Direction импорт қилинган
from django.db.models import Sum, Avg, Count # Avg ва Count керак эмас, агар фақат Sum ишлатилса
from django.http import JsonResponse
from collections import defaultdict # evaluate_view да керак бўлиши мумкин (агар tab'ли бўлса)
from django.utils.translation import gettext_lazy as _
from django.utils.translation import gettext # Динамик статус учун
from django.utils import translation
from io import BytesIO
import qrcode
from django.http import HttpResponse

def qr_code_view(request):
    base_url = request.build_absolute_uri('/final')  

    qr = qrcode.QRCode(
        version=1,
        box_size=10,
        border=5
    )
    qr.add_data(base_url)
    qr.make(fit=True)

    img = qr.make_image(fill='black', back_color='white')

    buf = BytesIO()
    img.save(buf)
    buf.seek(0)

    return HttpResponse(buf.getvalue(), content_type='image/png')


@login_required
def evaluate_view(request):
    current_user = request.user
    # all_criteria = Criterion.objects.all().order_by('order') # Буни home.html tab'ли версиясида ишлатгандик
    # Ҳозирги home.html (оддий жадвал) учун:
    all_criteria_list = list(Criterion.objects.all().order_by('order'))


    teams_to_show_qs = Team.objects.all()
    judge_assigned_directions = []
    is_judge_assigned_to_specific_directions = False

    try:
        judge_profile = current_user.judge_profile
        if judge_profile.assigned_direction:
            teams_to_show_qs = Team.objects.filter(direction=judge_profile.assigned_direction)
            judge_assigned_directions = [judge_profile.assigned_direction]
            is_judge_assigned_to_specific_directions = True
    except JudgeProfile.DoesNotExist:
        pass
    
    # Агар home.html tab'ли бўлса, бу ерда evaluation_data_by_direction яратилади
    # Ҳозирги home.html (оддий жадвал) учун:
    teams_evaluation_data = []
    for team in teams_to_show_qs.select_related('direction').prefetch_related('evaluation_set'):
        evaluations_by_judge_for_team = [
            ev for ev in team.evaluation_set.all() if ev.judge_id == current_user.id
        ]
        
        scores_by_criteria = {
            ev.criterion_id: ev.score for ev in evaluations_by_judge_for_team if ev.score is not None
        }
        statuses_by_criteria = {
            ev.criterion_id: ev.status for ev in evaluations_by_judge_for_team
        }
        
        evaluated_criteria_count = len(evaluations_by_judge_for_team)
        finalized_criteria_count = sum(1 for ev in evaluations_by_judge_for_team if ev.status == Evaluation.STATUS_FINAL)
        all_criteria_count = len(all_criteria_list)

        fully_finalized = (evaluated_criteria_count == all_criteria_count) and \
                            (finalized_criteria_count == all_criteria_count) and \
                            (all_criteria_count > 0)
        partially_finalized_or_all_draft = (evaluated_criteria_count == all_criteria_count) and not fully_finalized and (all_criteria_count > 0)

        teams_evaluation_data.append({
            'team': team,
            'scores_by_criteria': scores_by_criteria,
            'statuses_by_criteria': statuses_by_criteria,
            'evaluated_count': evaluated_criteria_count,
            'finalized_count': finalized_criteria_count,
            'total_criteria_count': all_criteria_count,
            'fully_finalized': fully_finalized,
            'partially_finalized_or_all_draft': partially_finalized_or_all_draft
        })
    
    context = {
        'teams_evaluation_data': teams_evaluation_data, # Оддий жадвал учун
        # 'evaluation_data_by_direction': dict(evaluation_data_by_direction), # Tab'ли версия учун
        # 'active_directions_for_tabs': active_directions_for_tabs, # Tab'ли версия учун
        'all_criteria': all_criteria_list, # Иккаласи учун ҳам керак
        'STATUS_FINAL': Evaluation.STATUS_FINAL,
        'STATUS_DRAFT': Evaluation.STATUS_DRAFT,
        # 'show_tabs': len(active_directions_for_tabs) > 1 or (...) # Tab'ли версия учун
    }
    return render(request, 'judging/home.html', context)


@login_required
def evaluate_team_view(request, team_id):
    team = get_object_or_404(Team, id=team_id)
    current_user = request.user

    can_evaluate_this_team = True
    judge_assigned_direction_name = "Все" # Дефолт
    try:
        judge_profile = current_user.judge_profile
        if judge_profile.assigned_direction:
            judge_assigned_direction_name = judge_profile.assigned_direction.name
            if team.direction != judge_profile.assigned_direction:
                can_evaluate_this_team = False
    except JudgeProfile.DoesNotExist:
        pass 

    if not can_evaluate_this_team:
        team_direction_name = team.direction.name if team.direction else "N/A"
        # criterion.name ва direction.name моделларидан рус тилида келиши керак
        messages.error(request, _(f"Вы можете оценивать команды только в направлении '{judge_assigned_direction_name}'. Эта команда ('{team.name}') относится к направлению '{team_direction_name}'."))
        return redirect('evaluate')

    criteria = Criterion.objects.all().order_by('order')
    existing_evaluations_qs = Evaluation.objects.filter(judge=current_user, team=team)
    scores = {eval.criterion_id: eval.score for eval in existing_evaluations_qs}
    statuses = {eval.criterion_id: eval.status for eval in existing_evaluations_qs}
    
    all_scores_final_for_this_judge_team = True
    if not criteria:
        all_scores_final_for_this_judge_team = False
    else:
        for criterion_obj in criteria:
            if statuses.get(criterion_obj.id) != Evaluation.STATUS_FINAL:
                all_scores_final_for_this_judge_team = False
                break
    
    if request.method == 'POST':
        if all_scores_final_for_this_judge_team:
            messages.warning(request, _("Оценки для этой команды уже были финализированы."))
            return redirect('evaluate_team', team_id=team.id)

        submission_status_choice = request.POST.get('submission_finality')
        if not submission_status_choice:
            messages.error(request, _("Тип сохранения оценок не выбран."))
            return redirect('evaluate_team', team_id=team.id)

        for criterion_item in criteria:
            score_str = request.POST.get(f'score_for_criterion_{criterion_item.id}') 
            current_eval = existing_evaluations_qs.filter(criterion=criterion_item).first()

            if current_eval and current_eval.status == Evaluation.STATUS_FINAL:
                if score_str and score_str.strip() and score_str.isdigit() and int(score_str) != current_eval.score:
                     messages.info(request, _(f"Оценка по критерию '{criterion_item.name}' уже итоговая и не была изменена."))
                elif submission_status_choice == Evaluation.STATUS_DRAFT:
                     messages.info(request, _(f"Оценка по критерию '{criterion_item.name}' уже итоговая и не может быть возвращена в черновик."))
                continue

            if score_str is not None and score_str.strip() != "":
                try:
                    score = int(score_str) 
                    if not (0 <= score <= criterion_item.max_score):
                        messages.error(request, _(f"Оценка по критерию '{criterion_item.name}' должна быть в диапазоне от 0 до {criterion_item.max_score}. Введено: '{score}'."))
                        continue
                    
                    Evaluation.objects.update_or_create(
                        judge=current_user,
                        team=team,
                        criterion=criterion_item,
                        defaults={'score': score, 'status': submission_status_choice}
                    )
                except ValueError:
                    messages.error(request, _(f"Неверный формат оценки ('{score_str}') для критерия '{criterion_item.name}'. Введите число."))
            elif submission_status_choice == Evaluation.STATUS_FINAL and current_eval and current_eval.score is not None and current_eval.status == Evaluation.STATUS_DRAFT:
                current_eval.status = Evaluation.STATUS_FINAL
                current_eval.save()
            # elif not score_str and current_eval and submission_status_choice == Evaluation.STATUS_DRAFT:
            #     pass # Логика для удаления оценки, если пусто и черновик (пока не реализовано)

        status_text = _("неизвестный")
        if submission_status_choice == Evaluation.STATUS_FINAL:
            status_text = _("Итоговая")
        elif submission_status_choice == Evaluation.STATUS_DRAFT:
            status_text = _("Черновик")
            
        messages.success(request, _(f"Оценки для команды '{team.name}' были сохранены/обновлены (статус: {status_text})."))
        # Олдинги `return redirect('evaluate')` ни ўзгартирдим, ўша саҳифага қайтиш учун
        return redirect('evaluate')


    default_submission_status = Evaluation.STATUS_DRAFT
    if all_scores_final_for_this_judge_team:
        default_submission_status = Evaluation.STATUS_FINAL

    context = {
        'team': team,
        'criteria': criteria,
        'scores': scores,
        'statuses': statuses,
        'all_scores_final': all_scores_final_for_this_judge_team,
        'STATUS_DRAFT': Evaluation.STATUS_DRAFT,
        'STATUS_FINAL': Evaluation.STATUS_FINAL,
        'default_submission_status': default_submission_status,
    }
    return render(request, 'judging/evaluate_team.html', context)


def public_results_view(request):
    # Бу view'да контекст керак эмас, чунки ҳаммаси JS орқали юкланади
    return render(request, 'judging/public_results.html')

def public_results_api_view(request):
    user_language_code = translation.get_language_from_request(request, check_path=False) 
    
    # Ҳозирги актив тилни ва аниқланган тилни чиқариб кўрамиз (дебаг учун)
    print(f"--- public_results_api_view ---")
    print(f"Language from request (get_language_from_request): {user_language_code}")
    print(f"Current active language before override (translation.get_language()): {translation.get_language()}")

    with translation.override(user_language_code):
        # Бу блок ичида актив тил user_language_code бўлиши керак
        print(f"Current active language INSIDE override (translation.get_language()): {translation.get_language()}")

        directions_qs = Direction.objects.all().order_by('name')
        all_directions_list = []
        for i, direction_obj in enumerate(directions_qs):
            # Ҳар бир объект учун унинг name атрибутининг қийматини чиқарамиз
            # Бу modeltranslation орқали актив тилда келиши керак
            print(f"  Direction {i+1} ('{direction_obj.id}'): name = '{direction_obj.name}'")
            # Агар аниқ тиллардаги майдонларни текширмоқчи бўлсангиз (базада бор-йўқлигини)
            # print(f"    name_ru: {getattr(direction_obj, 'name_ru', 'N/A')}")
            # print(f"    name_kaa: {getattr(direction_obj, 'name_kaa', 'N/A')}")
            # print(f"    name_en: {getattr(direction_obj, 'name_en', 'N/A')}") # Агар инглизча ҳам бўлса

            all_directions_list.append({
                'id': direction_obj.id,
                'name': direction_obj.name
            })

        # criteria_list_for_json учун ҳам худди шундай қилиш мумкин, агар Criterion.name ҳам таржима қилинса
        criteria_qs = Criterion.objects.all().order_by('order')
        criteria_list_for_json = []
        for i, criterion_obj in enumerate(criteria_qs):
                print(f"  Criterion {i+1} ('{criterion_obj.id}'): name = '{criterion_obj.name}'")
                criteria_list_for_json.append({
                'id': criterion_obj.id,
                'name': criterion_obj.name,
                'order': criterion_obj.order,
                'max_score': criterion_obj.max_score
            })
        
        results_by_direction_dict = {}

    for direction_data in all_directions_list: # Энди all_directions_list дан фойдаланамиз
        direction_id = direction_data['id']
        direction_name_translated = direction_data['name'] # Таржима қилинган ном

        teams_in_direction = Team.objects.filter(direction_id=direction_id)
        
        current_direction_results = []
        for team in teams_in_direction:
            team_total_final_score_sum_api = 0
            scores_by_criterion_sum_for_display_api = {}

            for criterion_data_json in criteria_list_for_json:
                crit_id = criterion_data_json['id']
                criterion_sum_data_api = Evaluation.objects.filter(
                    team=team, 
                    criterion_id=crit_id, 
                    status=Evaluation.STATUS_FINAL
                ).aggregate(criterion_total_sum_api=Sum('score'))
                
                criterion_sum_api = criterion_sum_data_api['criterion_total_sum_api'] if criterion_sum_data_api['criterion_total_sum_api'] is not None else 0
                scores_by_criterion_sum_for_display_api[crit_id] = criterion_sum_api
                team_total_final_score_sum_api += criterion_sum_api
            
            current_direction_results.append({
                'team_id': team.id,
                'team_name': team.name, # Агар Team.name ҳам таржима қилинса, бу ҳам актив тилда келади
                'team_direction_id': team.direction_id, 
                'team_direction_name': direction_name_translated, # Юқорида олинган таржима қилинган ном
                'scores_by_criterion': scores_by_criterion_sum_for_display_api,
                'total_score': team_total_final_score_sum_api
            })
        results_by_direction_dict[str(direction_id)] = sorted(current_direction_results, key=lambda x: x['total_score'], reverse=True)

    return JsonResponse({
        'directions': all_directions_list, 
        'results_by_direction': results_by_direction_dict,
        'criteria_list': criteria_list_for_json
    })



def team_evaluation_details_api_view(request, team_id):
    team = get_object_or_404(Team, id=team_id)
    
    # Жорий тилни аниқлаймиз ва активлаштирамиз (modeltranslation учун)
    user_language_code = translation.get_language_from_request(request, check_path=False)
    with translation.override(user_language_code):
        evaluations = Evaluation.objects.filter(team=team, status=Evaluation.STATUS_FINAL)\
                                    .select_related('judge', 'criterion')\
                                    .order_by('judge__username', 'criterion__order')

        # Маълумотларни ҳакамлар бўйича гуруҳлаймиз
        evaluations_by_judge = {}
        for e in evaluations:
            judge_username = e.judge.username
            if judge_username not in evaluations_by_judge:
                evaluations_by_judge[judge_username] = {
                    'judge_name': judge_username, 
                    'judge_fullname': e.judge.first_name + ' ' + e.judge.last_name,
                    'scores_by_criterion': [],
                    'total_score': 0
                }
            
            evaluations_by_judge[judge_username]['scores_by_criterion'].append({
                'criterion_id': e.criterion.id,
                'criterion_name': e.criterion.name, # modeltranslation орқали таржима қилинади
                'criterion_order': e.criterion.order,
                'score': e.score
            })
            evaluations_by_judge[judge_username]['total_score'] += e.score

        # Рўйхатга айлантирамиз ва умумий балл бўйича саралаймиз (ихтиёрий)
        detailed_results = sorted(
            list(evaluations_by_judge.values()), 
            key=lambda x: x['total_score'], 
            reverse=True
        )

        # Барча критерийлар рўйхатини ҳам жўнатамиз (жадвал сарлавҳалари учун)
        criteria_qs = Criterion.objects.all().order_by('order')
        all_criteria_list = []
        for criterion_obj in criteria_qs:
            all_criteria_list.append({
                'id': criterion_obj.id,
                'name': criterion_obj.name, # modeltranslation
                'order': criterion_obj.order,
            })

        response_data = {
            'team_name': team.name, # modeltranslation
            'results_by_judge': detailed_results,
            'all_criteria': all_criteria_list
        }
    return JsonResponse(response_data)