from django.contrib import admin
from django import forms
from django.contrib.auth.models import *
from django.contrib.auth.admin import UserAdmin
from django.contrib.admin import ModelAdmin
from simplevod.models import Feed, Category, Tvod, SimplevodUser, AuthUser, AuthUserUserPermissions
from simplevod.forms import FeedForm, CategoryForm, TvodForm, SimplevodUserForm
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Count        
from orderedmodel import OrderedModelAdmin        
from django.db.models import Q
from django.contrib.admin import SimpleListFilter        
from django.utils.translation import gettext as _ 
from django.db.models import Count        
from django.core.exceptions import ValidationError
   
from django.contrib import messages
        
import re        
import logging
logger = logging.getLogger('svod')
    
# The next statement will disable all logging calls less severe than ERROR
# Comment this next satement to see more logging.
logging.disable(logging.ERROR)
#logging.disable(logging.DEBUG)

SIMPLEVOD_GEEN_CATEGORY = ' -- Geen-- '
SIMPLEVOD_NEW_CATEGORY  = 'Nieuw'
IDAT_RECENT_CATEGORY    = '#recent-category'
IDAT_DEFAULT_CATEGORY   = '#category-999'

SIMPLEVOD_DUMMY_ETAG    = '00000-000x-0x00000000x00'

SIMPLEVOD_SOURCE_FTP        = 0
SIMPLEVOD_SOURCE_JSON       = 1
SIMPLEVOD_SOURCE_XML        = 2
SIMPLEVOD_SOURCE_FILE       = 3

SIMPLEVOD_SOURCE_NAME_FTP   = 'FTP'
SIMPLEVOD_SOURCE_NAME_JSON  = 'JSON'
SIMPLEVOD_SOURCE_NAME_XML   = 'XML'
SIMPLEVOD_SOURCE_NAME_FILE  = 'FILE'

ADMIN_CHANGE_PAGE = 0
ADMIN_ADD_PAGE = 1

def validate_linux_path(path):
    regex = re.compile(
        r'^[\'\"]?(?:/[^/]+)*[\'\"]?$', re.IGNORECASE)
    return regex.match(path)

def delete_user(modeladmin, request, queryset):
    for obj in queryset:
        SimplevodUser.objects.filter(administrator=obj.username).delete()
        obj.delete()

admin.site.disable_action('delete_selected')
def delete_selected_items(modeladmin, request, queryset):
    for obj in queryset:
        obj.delete()
   
def delete_selected_categories(modeladmin, request, queryset):
    for obj in queryset:
        obj_is_new = bool(obj.is_new)
        if obj_is_new:
            message = "Category -%s- can not be deleted." % SIMPLEVOD_NEW_CATEGORY
            messages.warning(request, message)
        else:
            obj.delete()

class FeedFilter(admin.SimpleListFilter):
    title = 'Bron'
    parameter_name = 'bron'

    def lookups(self, request, model_admin):
        adjusted_list_filter = []

        username = request.user.username
        objs = SimplevodUser.objects.filter(administrator=username)
        if len(objs) > 0:
            admin = objs[0]
            nof_feeds = len(objs)         
            if nof_feeds > 1:
                for user in objs:
                    #feeds = Feed.objects.filter(id=user.fk_feed_id)
                    feeds = Feed.objects.filter(id=user.fk_feed_id).exclude(is_django=False)
                    if len(feeds) > 0:
                        entry = (feeds[0].id, feeds[0].title)
                        adjusted_list_filter.append(entry)

                sorted_list_filter = sorted(adjusted_list_filter, key=lambda feed: feed[1])  
                return sorted_list_filter
            else:
                return adjusted_list_filter
        else:
            return adjusted_list_filter
    
    def queryset(self, request, queryset):
        if self.value():
            feed_id = self.value()
            #return queryset.filter(fk_feed_id=feed_id)
            return queryset.filter(fk_feed_id=feed_id).filter(fk_feed_id__is_django=True)
        else:
            #return queryset
            return queryset.filter(fk_feed_id__is_django=True)

class CategoryFilter(admin.SimpleListFilter):
    title = 'Categorie'
    parameter_name = 'categorie'

    def lookups(self, request, model_admin):
        username = request.user.username
        objs = SimplevodUser.objects.filter(administrator=username)

        adjusted_list_filter = []
        
        not_categorized =  (0, _(SIMPLEVOD_GEEN_CATEGORY))
        adjusted_list_filter.append(not_categorized)

        categories = {}

        if len(objs) > 0:
            admin = objs[0]
            
            for user in objs:
                if "bron" in request.GET:
                    #logger.exception("There is a - bron -")
                    bron_number = request.GET[u'bron']
                    #categories = Category.objects.filter(fk_feed_id=user.fk_feed_id).filter(fk_feed_id=bron_number)
                    categories = Category.objects.filter(fk_feed_id=user.fk_feed_id).filter(fk_feed_id=bron_number).filter(fk_feed_id__is_django=True)
                else:
                    #logger.exception("There is no - bron -")
                    #categories = Category.objects.filter(fk_feed_id=user.fk_feed_id)
                    categories = Category.objects.filter(fk_feed_id=user.fk_feed_id).filter(fk_feed_id__is_django=True)
                
                for cat in categories:
                    entry = (cat.id, cat.title)
                    adjusted_list_filter.append(entry)

            sorted_list_filter = sorted(adjusted_list_filter, key=lambda feed: feed[1])  
            return sorted_list_filter

        else:
            return adjusted_list_filter

    def queryset(self, request, queryset):
        is_new = False
        is_none = False

        if self.value():
            category_id = int(self.value())

            for choice in self.lookup_choices:
                filter_id = int(choice[0])
                filter_name = choice[1]
                filter_name = filter_name.strip()

                if category_id == filter_id:
                    if filter_name.lower().strip() == SIMPLEVOD_NEW_CATEGORY.lower().strip():
                        is_new = True
                    elif filter_name.lower().strip() == SIMPLEVOD_GEEN_CATEGORY.lower().strip():
                        is_none = True
            
            if is_new:
                #qs = queryset.filter(is_new=True).order_by('-id')
                qs = queryset.filter(is_new=True).filter(fk_feed_id__is_django=True).order_by('-id')
            elif is_none:
                #qs = queryset.filter(fk_category_id__isnull=True)
                qs = queryset.filter(fk_category_id__isnull=True).filter(fk_feed_id__is_django=True)
            else:
                #qs = queryset.filter(fk_category_id=category_id)
                qs = queryset.filter(fk_category_id=category_id).filter(fk_feed_id__is_django=True)
        else:
            #qs = queryset
            qs = queryset.filter(fk_feed_id__is_django=True)

        return qs

class MyUserAdmin(UserAdmin): 

    def save_model(self, request, obj, form, change):
        #logger.exception("MyUserAdmin - save_model -")
        username = obj.username
        superuser = bool(obj.is_superuser)
        SimplevodUser.objects.filter(administrator=username).update(is_superuser=superuser)
        obj.save()
        
    def get_form(self, request, obj=None, **kwargs):
        #logger.exception('- MyUserAdmin - get_form -')
        self.exclude = ("is_superuser", "is_staff", "groups")
        self.fieldsets[2][1]["fields"] = ('user_permissions', 'is_active')
        form = super(MyUserAdmin,self).get_form(request, obj, **kwargs)
        return form

    def has_add_permission(self, request, obj=None):
        objs = AuthUserUserPermissions.objects.filter(user=request.user.id).filter(permission='7')
        if len(objs) > 0:
            return True
        else:
            return False 

    def has_change_permission(self, request, obj=None):
        objs = AuthUserUserPermissions.objects.filter(user=request.user.id).filter(permission='8')
        if len(objs) > 0:
            return True
        else:
            return False 

    def has_delete_permission(self, request, obj=None):
        return False

    list_display = ('username', 'first_name', 'last_name', 'is_active', 'last_login', 'date_joined')
    list_filter = ('is_active',)
    actions = [delete_user]  

class SimplevodUserAdmin(admin.ModelAdmin):

    def save_model(self, request, obj, form, change):
        #logger.exception("SimplevodUserAdmin - save_model -")
        administrator = obj.administrator
        objs = AuthUser.objects.filter(username=administrator)
        if len(objs) > 0:
            admin = objs[0]
            obj.is_superuser = bool(admin.is_superuser)
        obj.save()

    def queryset(self, request):
        qs = super(SimplevodUserAdmin, self).queryset(request)

        username = request.user.username
        objs = SimplevodUser.objects.filter(administrator=username)
        if len(objs) > 0:
            admin = objs[0]
            if admin.is_superuser:
                return qs
            else:
                return qs.none() 
        else:
            return qs.none() 

    def has_add_permission(self, request, obj=None):
        objs = AuthUserUserPermissions.objects.filter(user=request.user.id).filter(permission='19')
        if len(objs) > 0:
            return True
        else:
            return False 

    def has_change_permission(self, request, obj=None):
        objs = AuthUserUserPermissions.objects.filter(user=request.user.id).filter(permission='20')
        if len(objs) > 0:
            return True
        else:
            return False 

    def has_delete_permission(self, request, obj=None):
        objs = AuthUserUserPermissions.objects.filter(user=request.user.id).filter(permission='21')
        if len(objs) > 0:
            return True
        else:
            return False 

    list_display = ('administrator_name', 'fk_feed_name', 'description_name')
    list_filter = ('administrator',)
    actions = [delete_selected_items]  

    def fk_feed_name(self, obj):
      return ("%s" % (obj.fk_feed)).upper()
    fk_feed_name.short_description = 'Bron'

    def administrator_name(self, obj):
      return ("%s" % (obj.administrator))
    administrator_name.short_description = 'Naam'

    def description_name(self, obj):
      return ("%s" % (obj.description))
    description_name.short_description = 'Beschrijving'

    ordering = ('id',)
    
    form = SimplevodUserForm

def feed_form_factory(obj):

    class RuntimeFeedForm(forms.ModelForm):

        def __init__(self, *args, **kwargs):
            super(RuntimeFeedForm, self).__init__(*args, **kwargs)
    
        title = forms.CharField(label=_("Titel"), max_length=50, widget=forms.TextInput(attrs={'size':'100'}))
        name = forms.CharField(label=_("Naam"), max_length=50, widget=forms.TextInput(attrs={'size':'100'}))
        style = forms.CharField(label=_("Stijl"), max_length=25, widget=forms.TextInput(attrs={'size':'100'}))
        url = forms.URLField(max_length=225, required=False, widget=forms.TextInput(attrs={'size':'100'}), error_messages={'required' : 'Enter a link to Simplevod Json Feed', 'invalid' : 'Enter a valid link like http://vod-upload.lijbrandt.net/simplevod/feed-name.jsonld'})
        xml = forms.CharField(label=_("Path"), max_length=225, required=False, widget=forms.TextInput(attrs={'size':'100'}))
        aantal_videos = forms.CharField(label=_("Videos"), initial='zie lijst', max_length=50, widget=forms.TextInput(attrs={'readonly':'readonly', 'size':'100'}))

        def clean(self):
            retrieve = int(self.cleaned_data.get('retrieve'))
            if retrieve == SIMPLEVOD_SOURCE_XML:
                xml = str(self.cleaned_data.get('xml')).strip()
                xml = xml.rstrip("/")
                if len(xml) == 0:
                    raise ValidationError("Veld voor locatie van xml files mag niet leeg zijn indien bron XML is.")
                else:
                    match = validate_linux_path(xml)
                    if not match:
                        raise ValidationError("Specificatie voor locatie van xml files voldoet niet aan formaat voor Linux padnamen.")
            
            elif retrieve == SIMPLEVOD_SOURCE_JSON:
                url = str(self.cleaned_data.get('url')).strip()
                if len(url) == 0:
                    raise ValidationError("Veld voor met URL link naar JSON data file mag niet leeg zijn indien bron JSON is.")

            elif retrieve == SIMPLEVOD_SOURCE_FILE:
                vod = str(self.cleaned_data.get('xml')).strip()
                vod = vod.rstrip("/")
                if len(vod) == 0:
                    raise ValidationError("Veld voor locatie van vod-files mag niet leeg zijn indien bron FILE is.")
                else:
                    match = validate_linux_path(vod)
                    if not match:
                        raise ValidationError("Specificatie voor locatie van vod-files voldoet niet aan formaat voor Linux padnamen.")
            
            return self.cleaned_data

        class Meta:
            model = Feed
 
    return RuntimeFeedForm

class FeedAdmin(admin.ModelAdmin):

    def save_model(self, request, obj, form, change):
        #logger.exception("FeedAdmin - save_model -")
        obj.etag = SIMPLEVOD_DUMMY_ETAG
        obj.name = ''.join(obj.name.split()).lower()
        obj.save()

        categories = Category.objects.filter(fk_feed_id=obj).filter(is_new=True)
        if len(categories) == 0:

            new_category = Category()
            new_category.idat = IDAT_RECENT_CATEGORY
            new_category.active = False
            new_category.is_new = True
            new_category.title = SIMPLEVOD_NEW_CATEGORY
            new_category.fk_feed = obj
            new_category.save()
            
            # add an additional message
            #messages.info(request, "Extra message here.")
            #messages.success(request, "Extra message here.")
            #messages.error(request, "Extra message here.")
            messages.warning(request, "When Feed was created a Category -Nieuw- was made automatically. Use -active- flag to show.")
    
    def get_formsets(self, request, obj=None, **kwargs):
        self.form = feed_form_factory(obj)
        return super(FeedAdmin, self).get_formsets(request, obj, **kwargs)
    
    def queryset(self, request):
        qs = super(FeedAdmin, self).queryset(request)
        fd = qs.exclude(is_django=False)
        return fd 

    def has_add_permission(self, request, obj=None):
        objs = AuthUserUserPermissions.objects.filter(user=request.user.id).filter(permission='31')
        if len(objs) > 0:
            return True
        else:
            return False 

    def has_change_permission(self, request, obj=None):
        objs = AuthUserUserPermissions.objects.filter(user=request.user.id).filter(permission='32')
        if len(objs) > 0:
            return True
        else:
            return False 

    def has_delete_permission(self, request, obj=None):
        objs = AuthUserUserPermissions.objects.filter(user=request.user.id).filter(permission='33')
        if len(objs) > 0:
            return True
        else:
            return False 

    list_per_page = 25

    def title_description(self, obj):
      return ("%s" % (obj.title))
    title_description.short_description = 'Titel'

    def name_description(self, obj):
      return ("%s" % (obj.name)).upper()
    name_description.short_description = 'Naam'

    def style_description(self, obj):
      return ("%s" % (obj.style))
    style_description.short_description = 'Stijl'

    def url_description(self, obj):
      return ("%s" % (obj.url))
    url_description.short_description = 'URL - linked data -'

    def xml_description(self, obj):
      return ("%s" % (obj.xml))
    xml_description.short_description = 'XML/FILE - location -'

    #list_display = ('title_description', 'name_description', 'style_description', 'url_description','aantal_videos')
    list_display = ('title_description', 'name_description', 'url_description', 'xml_description','aantal_videos')
    actions = [delete_selected_items]  

    search_fields = ('title', 'name')
    ordering = ('id',)
    fieldsets = [
            ('Identificatie',   {'fields': ['title', 'name', 'style']}),
            ('Url',             {'fields': ['url']}),
            ('Dir',             {'fields': ['xml']}),
            ('Data',            {'fields': ['retrieve']}),
            ('Aantal Videos',   {'fields': ['aantal_videos']})
        ]    
    form = FeedForm

def category_form_factory(obj, username, is_superuser):

    class RuntimeCategoryForm(forms.ModelForm):

        def __init__(self, *args, **kwargs):
            super(RuntimeCategoryForm, self).__init__(*args, **kwargs)
            #self.fields['fk_feed'].widget.attrs['disabled'] = True 
            if is_superuser:
                #self.fields['fk_feed'].queryset = Feed.objects.all().order_by('title')
                self.fields['fk_feed'].queryset = Feed.objects.exclude(is_django=False).order_by('title')
            else:
                #self.fields['fk_feed'].queryset = Feed.objects.filter(simplevoduser__administrator=username).order_by('title')
                self.fields['fk_feed'].queryset = Feed.objects.filter(simplevoduser__administrator=username).exclude(is_django=False).order_by('title')
    
        title = forms.CharField(label=_("Titel"), max_length=250, widget=forms.TextInput(attrs={'size':'100'}))
        active = forms.BooleanField(label=_("Actief"), required=False, initial=True)
        idat = forms.CharField(label=_("IDAT code"), max_length=50, initial=IDAT_DEFAULT_CATEGORY, widget=forms.TextInput(attrs={'size':'100'}))

        if is_superuser:
            #qs=Feed.objects.all().order_by('title')
            qs=Feed.objects.exclude(is_django=False).order_by('title')
        else:
            #qs=Feed.objects.filter(simplevoduser__administrator=username).order_by('title')
            qs=Feed.objects.filter(simplevoduser__administrator=username).exclude(is_django=False).order_by('title')


        fk_feed = forms.ModelChoiceField(label=_("Bron"),widget=forms.Select(attrs={'style': 'width:525px'}), queryset=qs)

        #is_new = forms.BooleanField(label=_("Nieuw"), required=False, initial=False)

        class Meta:
            model = Category
 
    return RuntimeCategoryForm

class CategoryAdmin(OrderedModelAdmin):
    #class Media:
    #    js = ("/static/scripts/simplevod.js",)

    def title_description(self, obj):
      return ("%s" % (obj.title))
    title_description.short_description = 'Titel'

    def active_description(self, obj):
      return ("%s" % (obj.active))
    active_description.short_description = 'Actief'

    def fk_feed_description(self, obj):
      return ("%s" % (obj.fk_feed))
    fk_feed_description.short_description = 'Bron'

    def reorder_description(self, obj):
      return obj.order
    reorder_description.short_description = 'Volgorde'

    def save_model(self, request, obj, form, change):
        #logger.exception("CategoryAdmin - save_model -")
    
        obj_is_new = bool(obj.is_new)
        if obj_is_new:
        
            title_value = obj.title
            title_value = title_value.strip()
            if title_value.lower() != SIMPLEVOD_NEW_CATEGORY.lower():
                obj.title = SIMPLEVOD_NEW_CATEGORY

                message = "Name Category -%s- can not be changed." % SIMPLEVOD_NEW_CATEGORY
                messages.warning(request, message)

        obj.oldorder = 0
        obj.save()

    def add_view(self, request, *args, **kwargs):
        result = super(CategoryAdmin, self).add_view(request, *args, **kwargs )
        
        # Look at the referer for a query string '^.*\?.*$'
        ref = request.META.get('HTTP_REFERER', '')
        if ref.find('?') != -1:
            # We've got a query string, set the session value
            request.session['filtered'] =  ref
        
        if request.POST.has_key('_save'):
            try:
                if request.session['filtered'] is not None:
                    result['Location'] = request.session['filtered']
                    request.session['filtered'] = None
            except:
                pass
        return result

    def get_list_display(self, request):
        username = request.user.username

        objs = SimplevodUser.objects.filter(administrator=username)
        if len(objs) > 0:      
            
            admin = objs[0]
            nof_feeds = len(objs)         
        
            if ("bron" in request.GET) or (nof_feeds <= 1 and not admin.is_superuser):
                #logger.exception("There is a - bron -")
                self.list_display = ['title_description', 'active', 'fk_feed_description', 'reorder']
            else:            
                #logger.exception("There is no - bron -")
                self.list_display = ['title_description', 'active', 'fk_feed_description']

        my_list_display = list(self.list_display)
        my_list_display = super(CategoryAdmin, self).get_list_display(request)
        return my_list_display
        
    def change_view(self, request, obj_id):
        result = super(CategoryAdmin, self).change_view(request, obj_id)
        
        # Look at the referer for a query string '^.*\?.*$'
        ref = request.META.get('HTTP_REFERER', '')
        if ref.find('?') != -1:
            # We've got a query string, set the session value
            request.session['filtered'] =  ref
        
        if request.POST.has_key('_save'):
            try:
                if request.session['filtered'] is not None:
                    result['Location'] = request.session['filtered']
                    request.session['filtered'] = None
            except:
                pass
        return result

    def get_formsets(self, request, obj=None, **kwargs):
        username = request.user.username

        objs = SimplevodUser.objects.filter(administrator=username)
        if len(objs) > 0:
            admin = objs[0]
            is_superuser = admin.is_superuser
            self.form = category_form_factory(obj, username, is_superuser)

        return super(CategoryAdmin, self).get_formsets(request, obj, **kwargs)
        
    def queryset(self, request):
        qs = super(CategoryAdmin, self).queryset(request)
        ct = qs.filter(fk_feed_id__is_django=True)
 
        username = request.user.username
        objs = SimplevodUser.objects.filter(administrator=username)
        if len(objs) > 0:
            values = []
            for user in objs:
                values.append(user.fk_feed_id)

            query = reduce(lambda q,value: q|Q(fk_feed_id=value), values, Q())  
            #logger.exception(query)
            return ct.filter(query)
        else:
            return ct.none() 
                     
    def has_add_permission(self, request, obj=None):
        objs = AuthUserUserPermissions.objects.filter(user=request.user.id).filter(permission='22')
        if len(objs) > 0:
            return True
        else:
            return False 

    def has_change_permission(self, request, obj=None):
        objs = AuthUserUserPermissions.objects.filter(user=request.user.id).filter(permission='23')
        if len(objs) > 0:
            return True
        else:
            return False 

    def has_delete_permission(self, request, obj=None):
        if obj:     
            obj_is_new = bool(obj.is_new)
            if obj_is_new:     
                return False 
    
        objs = AuthUserUserPermissions.objects.filter(user=request.user.id).filter(permission='24')
        if len(objs) > 0:
            return True
        else:
            return False 

    list_display = ('title_description', 'active', 'fk_feed_description', 'reorder')
    actions = [delete_selected_categories]  
    list_per_page = 25
    list_filter = (FeedFilter, 'active')
    search_fields = ('title',)
    #ordering = ('id',)
    
    ordering = ('order',)
    raw_id_fields = ('fk_feed', )
  
    #actions = [delete_categories]  
  
    fieldsets = [
           ('Identificatie',   {'fields': ['title']}),
           ('Status',   {'fields': ['active']}),
           ('Menu',        {'fields': ['fk_feed', 'idat']})
        ] 
    form = CategoryForm

def tvod_form_factory(self, username, is_superuser=None, category_id=None, feed_id=None):

    class RuntimeTvodForm(forms.ModelForm):
        feed_field = None
        category_field = None
        
        def __init__(self, *args, **kwargs):
        
            super(RuntimeTvodForm, self).__init__(*args, **kwargs)
            instance = getattr(self, 'instance', None)

            if instance and instance.id:
                feed_field = self.fields['fk_feed']
                category_field = self.fields['fk_category']
        
                self.fields['fk_feed'].required = False
                #self.fields['fk_feed'].widget.attrs['disabled'] = 'disabled'
                
                self.fields['fk_feed'].label = "Bron"
                self.fields['fk_category'].label = "Categorie"

                if feed_id:
                    #qsfeed=Feed.objects.filter(id=feed_id)
                    qsfeed=Feed.objects.filter(id=feed_id).exclude(is_django=False)

                    #qscategory=Category.objects.filter(fk_feed_id=feed_id).exclude(title=SIMPLEVOD_NEW_CATEGORY).order_by('title')   
                    #qscategory=Category.objects.filter(fk_feed_id=feed_id).filter(fk_feed_id__is_django=True).exclude(title=SIMPLEVOD_NEW_CATEGORY).order_by('title')   
                    qscategory=Category.objects.filter(fk_feed_id=feed_id).filter(fk_feed_id__is_django=True).filter(is_new=False).order_by('title')   

                else:
                    #qsfeed=Feed.objects.all()
                    qsfeed=Feed.objects.exclude(is_django=False)

                    #qscategory=Category.objects.all().exclude(title=SIMPLEVOD_NEW_CATEGORY).order_by('title')   
                    #qscategory=Category.objects.filter(fk_feed_id__is_django=True).exclude(title=SIMPLEVOD_NEW_CATEGORY).order_by('title')
                    qscategory=Category.objects.filter(fk_feed_id__is_django=True).filter(is_new=False).order_by('title')
                
                #self.fields['fk_feed'].queryset = Feed.objects.order_by('title')
                self.fields['fk_feed'].queryset = qsfeed
                
                #self.fields['fk_category'].queryset = Category.objects.exclude(title=SIMPLEVOD_NEW_CATEGORY).order_by('title')
                self.fields['fk_category'].queryset = qscategory
                       
        def clean_fk_feed(self):
            
            instance = getattr(self, 'instance', None)
            if instance:
                return instance.fk_feed
            else:
                return self.cleaned_data.get('fk_feed', None)
                
        def clean(self):
            
            feed = self.cleaned_data.get('fk_feed')
            if not feed:
                raise ValidationError("Kies een bron.")

            category = self.cleaned_data.get('fk_category')
            if category:
                if not is_superuser:
                    #feeds = Feed.objects.filter(simplevoduser__administrator=username)
                    feeds = Feed.objects.filter(simplevoduser__administrator=username).exclude(is_django=False)

                    found = False
                    for feed in feeds:
                        if feed.id == category.fk_feed_id:
                            found = True
                    if not found:
                        raise ValidationError("Kies een andere categorie.")
                        
            return self.cleaned_data
            
        title = forms.CharField(label=_("Titel"), max_length=250, widget=forms.TextInput(attrs={'size':'100'}))
        active = forms.BooleanField(label=_("Actief"), required=False, initial=True)
        productdescription = forms.CharField(label=_("Beschrijving"), max_length=250, widget=forms.TextInput(attrs={'size':'100'}))

        if feed_id:
            #qsfeed=Feed.objects.filter(id=feed_id)
            qsfeed=Feed.objects.filter(id=feed_id).exclude(is_django=False)
            #fk_feed = forms.ModelChoiceField(label=_("Bron"),widget=forms.Select(attrs={'style': 'width:525px'}), queryset=qsfeed, initial={'id': feed_id})

            #qscategory=Category.objects.filter(fk_feed_id=feed_id).exclude(title=SIMPLEVOD_NEW_CATEGORY).order_by('title')   
            #qscategory=Category.objects.filter(fk_feed_id=feed_id).filter(fk_feed_id__is_django=True).exclude(title=SIMPLEVOD_NEW_CATEGORY).order_by('title')   
            qscategory=Category.objects.filter(fk_feed_id=feed_id).filter(fk_feed_id__is_django=True).filter(is_new=False).order_by('title')   
 
            feed = Feed.objects.get(id=feed_id)
            if not feed.use_category:
                fk_category = forms.ModelChoiceField(label=_("Categorie"), required=False, widget=forms.Select(attrs={'style': 'width:225px'}), queryset=qscategory)
        else:
            #qsfeed=Feed.objects.all()
            qsfeed=Feed.objects.exclude(is_django=False)
            #fk_feed = forms.ModelChoiceField(label=_("Bron"),widget=forms.Select(attrs={'style': 'width:525px'}), queryset=qsfeed)

            #qscategory=Category.objects.all().exclude(title=SIMPLEVOD_NEW_CATEGORY).order_by('title')   
            qscategory=Category.objects.filter(fk_feed_id__is_django=True).filter(is_new=False).order_by('title')   

            #fk_category = forms.ModelChoiceField(label=_("Categorie"), required=False, widget=forms.Select(attrs={'style': 'width:525px'}), queryset=qscategory)

        if feed_field:
            feed_field.queryset = qsfeed
            
        if category_field:
            category_field.queryset = qscategory

        is_new = forms.BooleanField(label=_("Nieuw"), required=False, initial=False)
        
        class Meta:
            model = Tvod
 
    return RuntimeTvodForm


class TvodAdmin(OrderedModelAdmin):

    #class Media:
    #    js = ("/static/scripts/simplevod.js")
        
    def title_description(self, obj):
      return ("%s" % (obj.title))
    title_description.short_description = 'Titel'

    def active_description(self, obj):
      return ("%s" % (obj.active))
    active_description.short_description = 'Actief'

    def product_description(self, obj):
      return ("%s" % (obj.productdescription))
    product_description.short_description = 'Beschrijving'

    def fk_feed_description(self, obj):
      return ("%s" % (obj.fk_feed))
    fk_feed_description.short_description = 'Bron'

    def fk_category_description(self, obj):
      return ("%s" % (obj.fk_category))
    fk_category_description.short_description = 'Categorie'

    def reorder_description(self, obj):
      return obj.order
    reorder_description.short_description = 'Volgorde'

    def get_list_display(self, request):
        username = request.user.username
        objs = SimplevodUser.objects.filter(administrator=username)
        if len(objs) > 0:      
            admin = objs[0]
            nof_feeds = len(objs)         
        
            is_new = False
            is_none = False

            if (("bron" in request.GET) and ("categorie" in request.GET)) or ((nof_feeds <= 1 and not admin.is_superuser) and ("categorie" in request.GET)):
                categorie_number = int(request.GET[u'categorie'])

                #objs = Category.objects.filter(id=categorie_number)
                objs = Category.objects.filter(id=categorie_number).filter(fk_feed_id__is_django=True)
                if len(objs) > 0:
                    filter_name = str(objs[0])

                    first_record = objs[0]
                    first_record_is_new = bool(first_record.is_new)
                    
                    #if filter_name.lower().strip() == SIMPLEVOD_NEW_CATEGORY.lower().strip():
                    if first_record_is_new:
                        is_new = True
                    elif filter_name.lower().strip() == SIMPLEVOD_GEEN_CATEGORY.lower().strip():
                        is_none = True

                if is_new or is_none:
                    self.list_display = ['title_description', 'active', 'fk_feed_description', 'fk_category_description', 'is_new']
                    self.ordering = ('-idat', '-id')
                else:
                    self.list_display = ['title_description', 'active', 'fk_feed_description', 'fk_category_description', 'is_new', 'reorder']
                    self.ordering = ('order',)
            else:            
                self.list_display = ['title_description', 'active', 'fk_feed_description', 'fk_category_description', 'is_new']
                self.ordering = ('order',)

        my_list_display = list(self.list_display)
        my_list_display = super(TvodAdmin, self).get_list_display(request)
        return my_list_display

    def add_view(self, request, *args, **kwargs):
        result = super(TvodAdmin, self).add_view(request, *args, **kwargs )
        
        # Look at the referer for a query string '^.*\?.*$'
        ref = request.META.get('HTTP_REFERER', '')
        if ref.find('?') != -1:
            # We've got a query string, set the session value
            request.session['filtered'] =  ref
        
        if request.POST.has_key('_save'):
            try:
                if request.session['filtered'] is not None:
                    result['Location'] = request.session['filtered']
                    request.session['filtered'] = None
            except:
                pass

        return result

    def change_view(self, request, obj_id):
        result = super(TvodAdmin, self).change_view(request, obj_id)
        
        # Look at the referer for a query string '^.*\?.*$'
        ref = request.META.get('HTTP_REFERER', '')
        if ref.find('?') != -1:
            # We've got a query string, set the session value
            request.session['filtered'] =  ref
        
        if request.POST.has_key('_save'):
            try:
                if request.session['filtered'] is not None:
                    result['Location'] = request.session['filtered']
                    request.session['filtered'] = None
            except:
                pass
                
        return result

    def get_formsets(self, request, obj=None, **kwargs):

        is_superuser = None
        category_id = None
        feed_id = None

        username = request.user.username
        objs = SimplevodUser.objects.filter(administrator=username)

        if len(objs) > 0:
            admin = objs[0]
            is_superuser = bool(admin.is_superuser)

        path_info = request.META.get('PATH_INFO', '')
        result = re.findall(r'\b\d+\b', path_info)
        if result[0].isnumeric():
            tvod_id = result[0]

            #tvods = Tvod.objects.filter(id=tvod_id)
            tvods = Tvod.objects.filter(id=tvod_id).filter(fk_feed_id__is_django=True)
            if len(tvods) > 0:
                tvod_record = tvods[0]
                feed_id = tvod_record.fk_feed_id 
                category_id = tvod_record.fk_category_id 
        
        self.form = tvod_form_factory(self, username, is_superuser, category_id, feed_id)
            
        return super(TvodAdmin, self).get_formsets(request, obj, **kwargs)

    def queryset(self, request):
        qs = super(TvodAdmin, self).queryset(request)
        tv = qs.filter(fk_feed_id__is_django=True)
        
        username = request.user.username
        objs = SimplevodUser.objects.filter(administrator=username)
        if len(objs) > 0:
            values = []
            for user in objs:
                values.append(user.fk_feed_id)

            query = reduce(lambda q,value: q|Q(fk_feed_id=value), values, Q())  
            #logger.exception(query)
            return tv.filter(query)
        else:
            return tv.none() 

    def has_add_permission(self, request, obj=None):
        return False 

    def has_change_permission(self, request, obj=None):
        objs = AuthUserUserPermissions.objects.filter(user=request.user.id).filter(permission='26')
        if len(objs) > 0:
            return True
        else:
            return False 

    def has_delete_permission(self, request, obj=None):
        objs = AuthUserUserPermissions.objects.filter(user=request.user.id).filter(permission='27')
        if len(objs) > 0:
            return True
        else:
            return False 
    
        username = request.user.username
        objs = SimplevodUser.objects.filter(administrator=username)
        if len(objs) > 0:
            admin = objs[0]
            if admin.is_superuser:
                return True
            else:
                return False 
        else:
            return False 

    list_per_page = 25
    list_display = ('title_description', 'active', 'fk_feed_description', 'fk_category_description', 'is_new', 'reorder')
    actions = [delete_selected_items]  
    list_filter = (FeedFilter, CategoryFilter, 'active')
    preserve_filters = True

    search_fields = ('title',)
    #ordering = ('id',)
    ordering = ('order',)

    fieldsets = [
           ('Identificatie',   {'fields': ['title', 'productdescription']}),
           ('Status',   {'fields': ['active', 'is_new']}),
           ('Menu',        {'fields': ['fk_feed', 'fk_category']})
        ]
    
    form = TvodForm

admin.site.register(SimplevodUser, SimplevodUserAdmin)
admin.site.register(Feed, FeedAdmin)
admin.site.register(Category, CategoryAdmin)
admin.site.register(Tvod, TvodAdmin)
admin.site.unregister(User)
admin.site.unregister(Group)

#admin.site.unregister(User)
#admin.site.register(User, UserAdmin)
admin.site.register(User, MyUserAdmin)
#admin.site.unregister(Group)




