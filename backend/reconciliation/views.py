from django.shortcuts import render

# Create your views here.
from django.http import JsonResponse
from reconciliation.services import run_reconciliation


def disagreements_api(request):
    """
    GET /api/disagreements/
    Returns the full list of detected reconciliation disagreements in JSON format.
    """
    disagreements = run_reconciliation()
    return JsonResponse({
        "count": len(disagreements),
        "disagreements": disagreements
    }, safe=False)
