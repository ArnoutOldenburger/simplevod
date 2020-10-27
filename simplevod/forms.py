import re 

from django import forms
from django.contrib import admin
from django.contrib.auth.models import User
from django.db import connection, models
from django.utils.translation import gettext as _
from simplevod.models import Feed, Category, Tvod, SimplevodUser
from django.core.exceptions import ValidationError

import logging
logger = logging.getLogger('svod')

SIMPLEVOD_NEW_CATEGORY  = 'Nieuw'
IDAT_RECENT_CATEGORY    = '#recent-category'
IDAT_DEFAULT_CATEGORY   = '#category-999'

SIMPLEVOD_SOURCE_FTP        = 0
SIMPLEVOD_SOURCE_JSON       = 1
SIMPLEVOD_SOURCE_XML        = 2
SIMPLEVOD_SOURCE_FILE       = 3

SIMPLEVOD_SOURCE_NAME_FTP   = 'FTP'
SIMPLEVOD_SOURCE_NAME_JSON  = 'JSON'
SIMPLEVOD_SOURCE_NAME_XML   = 'XML'  
SIMPLEVOD_SOURCE_NAME_FILE  = 'FILE'

class SimplevodUserForm(forms.ModelForm):
    administrator = forms.ModelChoiceField(label=_("Beheerder"), required=True, widget=forms.Select(attrs={'style': 'width:525px'}), queryset=User.objects.all())
    fk_feed = forms.ModelChoiceField(label=_("Bron"), widget=forms.Select(attrs={'style': 'width:525px'}), queryset=Feed.objects.filter(is_django=True).order_by('title'))
    description = forms.CharField(label=_("Omschrijving"), required=False, max_length=50, widget=forms.TextInput(attrs={'size':'100'}))

    class Meta:
        model = SimplevodUser

def validate_linux_path(path):
    regex = re.compile(
        r'^[\'\"]?(?:/[^/]+)*[\'\"]?$', re.IGNORECASE)

    return regex.match(path)

class FeedForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        super(FeedForm, self).__init__(*args, **kwargs)
        #self.fields['retrieve'].widget.attrs['disabled'] = True 
        #self.data.update({ 'retrieve': self.instance.retrieve })

    def clean(self):
    
        retrieve = int(self.cleaned_data.get('retrieve'))
        
        if retrieve == SIMPLEVOD_SOURCE_XML:
            xml = str(self.cleaned_data.get('xml')).strip()
            if len(xml) == 0:
                raise ValidationError("Veld voor locatie van xml-files mag niet leeg zijn indien bron XML is.")
            else:
                match = validate_linux_path(xml)
                if not match:
                    raise ValidationError("Specificatie voor locatie van xml-files voldoet niet aan formaat voor Linux padnamen.")
        
        elif retrieve == SIMPLEVOD_SOURCE_JSON:
            url = str(self.cleaned_data.get('url')).strip()
            if len(url) == 0:
                raise ValidationError("Veld voor met URL link naar JSON data file mag niet leeg zijn indien bron JSON is.")

        elif retrieve == SIMPLEVOD_SOURCE_FILE:
            vod = str(self.cleaned_data.get('xml')).strip()
            if len(vod) == 0:
                raise ValidationError("Veld voor locatie van vod-files mag niet leeg zijn indien bron FILE is.")
            else:
                match = validate_linux_path(vod)
                if not match:
                    raise ValidationError("Specificatie voor locatie van vod-files voldoet niet aan formaat voor Linux padnamen.")
        
        return self.cleaned_data

    title = forms.CharField(label=_("Titel"), max_length=50, widget=forms.TextInput(attrs={'size':'100'}))
    name = forms.CharField(label=_("Naam"), max_length=50, widget=forms.TextInput(attrs={'size':'100'}))
    style = forms.CharField(label=_("Stijl"), max_length=25, widget=forms.TextInput(attrs={'size':'100'}))
    url = forms.URLField(max_length=225, required=False, widget=forms.TextInput(attrs={'size':'100'}), error_messages={'required' : 'Enter a link to Simplevod Json Feed', 'invalid' : 'Enter a valid link like http://vod-upload.lijbrandt.net/simplevod/feed-name.jsonld'})
    xml = forms.CharField(label=_("Path"), max_length=225, required=False, widget=forms.TextInput(attrs={'size':'100'}))
    aantal_videos = forms.CharField(label=_("Videos"), initial='zie lijst', max_length=50, widget=forms.TextInput(attrs={'readonly':'readonly', 'size':'100'}))

    class Meta:
        model = Feed

class CategoryForm(forms.ModelForm):

    #def __init__(self, *args, **kwargs):
    #    super(CategoryForm, self).__init__(*args, **kwargs)
    #    self.fields['fk_feed'].widget.attrs['disabled'] = True 

    title = forms.CharField(label=_("Titel"), max_length=50, widget=forms.TextInput(attrs={'size':'100'}))
    active = forms.BooleanField(label=_("Actief"), required=False, initial=True)
    idat = forms.CharField(label=_("IDAT code"), max_length=50, initial=IDAT_DEFAULT_CATEGORY, widget=forms.TextInput(attrs={'size':'100'}))
    #fk_feed = forms.ModelChoiceField(label=_("Bron"), widget=forms.Select(attrs={'style': 'width:525px'}), queryset=Feed.objects.all().order_by('title'))
    fk_feed = forms.ModelChoiceField(label=_("Bron"), widget=forms.Select(attrs={'style': 'width:525px'}), queryset=Feed.objects.filter(is_django=True).order_by('title'))
    #is_new = forms.BooleanField(label=_("Nieuw"), required=False, initial=False)

    class Meta:
        model = Category

class TvodForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        #logger.exception("TvodForm - __init__")
        super(TvodForm, self).__init__(*args, **kwargs)

        instance = getattr(self, 'instance', None)
        if instance and instance.id:
            self.fields['fk_feed'].required = False
            #self.fields['fk_feed'].widget.attrs['disabled'] = 'disabled'
            
            self.fields['fk_feed'].label = "Bron"
            self.fields['fk_category'].label = "Categorie"

            self.fields['fk_feed'].queryset = Feed.objects.order_by('title')
            self.fields['fk_category'].queryset = Category.objects.exclude(title=SIMPLEVOD_NEW_CATEGORY).order_by('title')

    def clean_fk_feed(self):
        instance = getattr(self, 'instance', None)
        if instance:
            return instance.fk_feed
        else:
            return self.cleaned_data.get('fk_feed', None)
                
    title = forms.CharField(label=_("Titel"), max_length=250, widget=forms.TextInput(attrs={'size':'100'}))
    active = forms.BooleanField(label=_("Actief"), required=False, initial=True)
    productdescription = forms.CharField(label=_("Beschrijving"), max_length=250, widget=forms.TextInput(attrs={'size':'100'}))
    fk_feed = forms.ModelChoiceField(label=_("Bron"), queryset=Feed.objects.all().order_by('title'))
    fk_category = forms.ModelChoiceField(label=_("Categorie"), queryset=Category.objects.all().exclude(title=SIMPLEVOD_NEW_CATEGORY).order_by('title'),required=False)
    is_new = forms.BooleanField(label=_("Nieuw"), required=False, initial=False)

    class Meta:
        model = Tvod



