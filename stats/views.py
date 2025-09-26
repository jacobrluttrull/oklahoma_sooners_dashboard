from django.http import HttpResponse

def home(request):
    return HttpResponse("Boomer Sooner! Oklahoma Dashboard is live.")

