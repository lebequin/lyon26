import json
import os

from django.http import JsonResponse
from django.views.generic import TemplateView
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.conf import settings
from django.db.models import Sum

from territory.models import VotingDesk
from ..models import ElectionResult, Election, Alliance, ElectionParticipation, NuanceResult, Nuance


class ElectionsListView(LoginRequiredMixin, TemplateView):
    """Election results by voting desk with trends"""
    template_name = 'mobilisation/elections_list.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        results = ElectionResult.objects.select_related('voting_desk').all()
        context['results'] = results

        if results.exists():
            context['avg_reg21'] = sum(r.reg21_uge_percent for r in results) / len(results)
            context['avg_euro24'] = sum(r.euro24_nfp_percent for r in results) / len(results)
            context['avg_leg24'] = sum(r.leg24_nfp_percent for r in results) / len(results)

            context['bv_codes'] = [r.voting_desk.code for r in results]
            context['reg21_data'] = [r.reg21_uge_percent for r in results]
            context['euro24_data'] = [r.euro24_nfp_percent for r in results]
            context['leg24_data'] = [r.leg24_nfp_percent for r in results]
            context['delta_data'] = [r.delta_nfp_percent for r in results]

            context['trend_up'] = sum(1 for r in results if r.delta_nfp_percent > 2)
            context['trend_down'] = sum(1 for r in results if r.delta_nfp_percent < -2)
            context['trend_stable'] = len(results) - context['trend_up'] - context['trend_down']
        else:
            context['avg_reg21'] = 0
            context['avg_euro24'] = 0
            context['avg_leg24'] = 0
            context['bv_codes'] = []
            context['reg21_data'] = []
            context['euro24_data'] = []
            context['leg24_data'] = []
            context['delta_data'] = []
            context['trend_up'] = 0
            context['trend_down'] = 0
            context['trend_stable'] = 0

        return context


class StrategyView(LoginRequiredMixin, TemplateView):
    """Strategy dashboard: participation & political comparison per voting desk."""
    template_name = 'mobilisation/strategy.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        all_elections = list(Election.objects.all().order_by('year', 'round'))
        context['all_elections'] = all_elections

        selected_ids = self.request.GET.getlist('elections')[:3]
        sort_by = self.request.GET.get('sort', 'reserve')
        context['selected_ids'] = selected_ids
        context['sort_by'] = sort_by

        if not selected_ids:
            context['desk_rows'] = []
            return context

        selected_elections = [e for e in all_elections if e.election_code in selected_ids]

        desks_electors = {
            vd.code: (vd.total_electors or 0)
            for vd in VotingDesk.objects.annotate(total_electors=Sum('buildings__elector_count'))
        }

        participations = ElectionParticipation.objects.filter(
            election__election_code__in=selected_ids
        ).select_related('election', 'voting_desk')

        part_index = {}
        desk_codes = set()
        for p in participations:
            code = p.voting_desk.code
            desk_codes.add(code)
            part_index.setdefault(code, {})[p.election.election_code] = p.abstention_percent

        nuance_results = NuanceResult.objects.filter(
            election__election_code__in=selected_ids,
            voting_desk__code__in=desk_codes
        ).select_related('election', 'voting_desk', 'nuance')

        results_index = {}
        for nr in nuance_results:
            code = nr.voting_desk.code
            eid = nr.election.election_code
            results_index.setdefault(code, {}).setdefault(eid, {})[nr.nuance.code] = nr.vote_share

        alliances = list(Alliance.objects.prefetch_related('nuances').all())
        nuance_to_alliance = {}
        for alliance in alliances:
            for nuance in alliance.nuances.all():
                nuance_to_alliance[nuance.code] = alliance

        nuances_map = {n.code: n for n in Nuance.objects.all()}

        desks = {vd.code: vd for vd in VotingDesk.objects.filter(code__in=desk_codes)}

        desk_rows = []
        for desk_code in desk_codes:
            desk = desks.get(desk_code)
            if not desk:
                continue
            elector_count = desks_electors.get(desk_code, 0)

            elections_data = []
            abs_values = []

            for election in selected_elections:
                eid = election.election_code
                abs_pct = part_index.get(desk_code, {}).get(eid)
                if abs_pct is None:
                    elections_data.append(None)
                    continue

                abs_values.append(abs_pct)
                participation = round(100 - abs_pct, 1)
                reserve_brute = round((abs_pct / 100) * elector_count)

                nuance_scores = results_index.get(desk_code, {}).get(eid, {})
                seen = set()
                blocks = []

                for alliance in alliances:
                    score = sum(nuance_scores.get(n.code, 0) for n in alliance.nuances.all())
                    if score > 0:
                        blocks.append({
                            'label': alliance.name,
                            'short': alliance.name[:12],
                            'color': alliance.color,
                            'score': round(score, 1),
                            'is_alliance': True,
                        })
                        for n in alliance.nuances.all():
                            seen.add(n.code)

                for nc, score in sorted(nuance_scores.items(), key=lambda x: -x[1]):
                    if nc not in seen and score > 0:
                        nuance = nuances_map.get(nc)
                        blocks.append({
                            'label': nc,
                            'short': nc,
                            'color': nuance.color if nuance else '#6b7280',
                            'score': round(score, 1),
                            'is_alliance': False,
                        })

                blocks.sort(key=lambda x: -x['score'])

                cumul = 0
                stops = []
                for b in blocks:
                    start = round(cumul, 1)
                    end = round(cumul + b['score'], 1)
                    stops.append(f"{b['color']} {start}% {end}%")
                    cumul = end
                gradient = f"linear-gradient(to right, {', '.join(stops)})" if stops else None

                elections_data.append({
                    'election': election,
                    'abstention': abs_pct,
                    'participation': participation,
                    'reserve_brute': reserve_brute,
                    'blocks': blocks,
                    'gradient': gradient,
                })

            valid = [e for e in elections_data if e is not None]
            delta_participation = None
            if len(valid) >= 2:
                delta_participation = round(valid[-1]['participation'] - valid[0]['participation'], 1)

            if len(valid) >= 2:
                abs_values_valid = [e['abstention'] for e in valid]
                abs_max = max(abs_values_valid)
                abs_min = min(abs_values_valid)
                reserve_elastique = round(((abs_max - abs_min) / 100) * elector_count)
            elif len(valid) == 1:
                reserve_elastique = valid[0]['reserve_brute']
            else:
                reserve_elastique = 0

            latest = valid[-1] if valid else None
            priority_score = round(latest['abstention'], 1) if latest else 0

            desk_rows.append({
                'desk': desk,
                'elector_count': elector_count,
                'elections_data': elections_data,
                'delta_participation': delta_participation,
                'priority_score': priority_score,
                'reserve_elastique': reserve_elastique,
            })

        if sort_by == 'abstention':
            desk_rows.sort(key=lambda r: -r['priority_score'])
        elif sort_by == 'delta':
            desk_rows.sort(key=lambda r: (r['delta_participation'] is None, r['delta_participation'] or 0))
        else:
            desk_rows.sort(key=lambda r: -r['reserve_elastique'])

        context['desk_rows'] = desk_rows
        context['selected_elections'] = selected_elections

        if desk_rows:
            context['total_reserve'] = sum(r['reserve_elastique'] for r in desk_rows)
            deltas = [r['delta_participation'] for r in desk_rows if r['delta_participation'] is not None]
            context['avg_delta'] = round(sum(deltas) / len(deltas), 1) if deltas else None
            context['nb_bureaux'] = len(desk_rows)

            last_eid = selected_elections[-1].election_code if selected_elections else None
            total_expressed = 0
            for r in desk_rows:
                for edata in r['elections_data']:
                    if edata and edata['election'].election_code == last_eid:
                        total_expressed += round((edata['participation'] / 100) * r['elector_count'])
            context['total_expressed'] = total_expressed
            context['last_election_label'] = selected_elections[-1].name if selected_elections else ''

        return context


class StrategyAPIView(LoginRequiredMixin, View):
    """GeoJSON API for the strategy hot spots map."""

    def get(self, request):
        geojson_path = os.path.join(settings.BASE_DIR, 'static', 'data', 'bureaux_vote_lyon5.geojson')
        try:
            with open(geojson_path, 'r') as f:
                geojson_data = json.load(f)
        except FileNotFoundError:
            return JsonResponse({'error': 'GeoJSON file not found'}, status=404)

        alliance_id = request.GET.get('alliance')
        election_ids = request.GET.getlist('elections')

        participations = ElectionParticipation.objects.select_related('election', 'voting_desk')
        if election_ids:
            participations = participations.filter(election__election_code__in=election_ids)

        part_index = {}
        for p in participations:
            code = p.voting_desk.code
            if code not in part_index:
                part_index[code] = {}
            part_index[code][p.election.election_code] = p.abstention_percent

        alliance_index = {}
        if alliance_id:
            try:
                alliance = Alliance.objects.prefetch_related('nuances').get(pk=alliance_id)
                nuance_codes = list(alliance.nuances.values_list('code', flat=True))

                results = NuanceResult.objects.filter(
                    nuance__code__in=nuance_codes
                ).select_related('election', 'voting_desk', 'nuance')
                if election_ids:
                    results = results.filter(election__election_code__in=election_ids)

                for r in results:
                    code = r.voting_desk.code
                    eid = r.election.election_code
                    if code not in alliance_index:
                        alliance_index[code] = {}
                    alliance_index[code][eid] = alliance_index[code].get(eid, 0) + r.vote_share
            except Alliance.DoesNotExist:
                pass

        desks_coverage = {}
        for desk in VotingDesk.objects.annotate(
            total_knocked=Sum('buildings__visits__knocked_doors'),
            total_electors=Sum('buildings__elector_count'),
        ):
            electors = desk.total_electors or 0
            knocked = desk.total_knocked or 0
            desks_coverage[desk.code] = round((knocked / electors * 100), 1) if electors > 0 else 0

        for feature in geojson_data['features']:
            numero = str(feature['properties'].get('numero', ''))
            part_data = part_index.get(numero, {})
            alliance_data = alliance_index.get(numero, {})
            couverture = desks_coverage.get(numero, 0)

            avg_abs = sum(part_data.values()) / len(part_data) if part_data else 0
            avg_score = sum(alliance_data.values()) / len(alliance_data) if alliance_data else 0

            pap_gap = 100 - couverture
            priority = round((avg_abs * 0.4) + (avg_score * 0.4) + (pap_gap * 0.2), 1)

            feature['properties']['strategy'] = {
                'avg_abstention': round(avg_abs, 1),
                'avg_alliance_score': round(avg_score, 1),
                'couverture_pap': couverture,
                'priority_score': priority,
                'participations': part_data,
                'alliance_scores': alliance_data,
            }

        return JsonResponse(geojson_data)


class VotingDeskBoundariesAPIView(LoginRequiredMixin, View):
    """GeoJSON API endpoint for voting desk boundaries with election data"""

    def get(self, request):
        geojson_path = os.path.join(settings.BASE_DIR, 'static', 'data', 'bureaux_vote_lyon5.geojson')

        try:
            with open(geojson_path, 'r') as f:
                geojson_data = json.load(f)
        except FileNotFoundError:
            return JsonResponse({'error': 'GeoJSON file not found'}, status=404)

        election_results = {}
        for result in ElectionResult.objects.select_related('voting_desk').all():
            code = result.voting_desk.code
            election_results[code] = {
                'leg24_nfp_percent': result.leg24_nfp_percent,
                'euro24_nfp_percent': result.euro24_nfp_percent,
                'reg21_uge_percent': result.reg21_uge_percent,
                'delta_nfp_percent': result.delta_nfp_percent,
                'neighborhood': result.neighborhood,
            }

        for feature in geojson_data['features']:
            numero = str(feature['properties'].get('numero', ''))
            if numero in election_results:
                feature['properties']['election'] = election_results[numero]
            else:
                feature['properties']['election'] = None

        return JsonResponse(geojson_data)
