"""ModelAdmin for Sender"""
from django import forms
from django.contrib import admin
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _

from emencia.django.newsletter.models import Sender


#class SenderAdminForm(forms.ModelForm):
    #"""Form ofr Sender with custom validation"""

    #class Meta:
        #model = Sender


class SenderAdmin(admin.ModelAdmin):
    date_hierarchy = 'creation_date'
    list_display = ('from_name', 'from_email', 'reply_name', 'reply_email')
    list_filter = ('from_email', 'creation_date', 'modification_date')
    search_fields = ('from_name', 'from_email', 'reply_name', 'reply_email')
    fieldsets = ((_('From info'), {'fields': ('from_name', 'from_email')}),
                 (_('Reply-to Info'), {'fields': ('reply_name', 'reply_email'),
                                       'classes': ('collapse', )}),
                 )
