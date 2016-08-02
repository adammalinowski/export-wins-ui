import datetime

from django.conf import settings
from django.http import HttpResponse
from django.views.generic import View

from alice.braces import LoginRequiredMixin
from alice.helpers import rabbit


class CSVView(LoginRequiredMixin, View):
    """ Get Zip of CSVs of current data from Data server """

    def get(self, request):
        data_response = rabbit.get(settings.CSV_AP, request=request)
        today_date = datetime.datetime.utcnow().strftime('%Y-%m-%d')
        filename = 'ew-data-{}.zip'.format(today_date)
        resp = HttpResponse(data_response, content_type='application/zip')
        resp['Content-Disposition'] = 'attachment; filename=' + filename
        return resp
