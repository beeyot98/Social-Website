import profile
from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from django.contrib.auth.models import User
from django.contrib import messages
from django.views.decorators.http import require_POST
from .forms import LoginForm, UserRegistrationForm, UserEditForm, ProfileEditForm
from .models import Profile,  Contact
from common.decorators import ajax_required
from actions.utils import create_actions
from actions.models import Action


# Create your views here.
def user_login(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)

        if form.is_valid():
            cd = form.cleaned_data
            user = authenticate(request,
                                username=cd['username'],
                                password=cd['password'])
            if user is not None:
                if user.is_active:
                    login(request, user)
                    return HttpResponse('Authenticated successfully')
                
                else:
                    return HttpResponse('Disabled account')
            else:
                return HttpResponse('Invalid Login')
        
    else:
        form = LoginForm()
    context = {'form': form}
    return render(request, 'account/login.html', context)

@login_required
def dashboard(request):
    actions = Action.objects.exclude(user=request.user)
    following_ids = request.user.following.values_list('id',flat=True)
    if following_ids:
        actions = actions.filter(user_id__in=following_ids)
    actions = actions.select_related('user', 'user__profile')\
.prefetch_related('target')[:10]

    context = {'section':'dashboard','actions':actions}
    return render(request, 'account/dashboard.html', context)

def register(request):
    if request.method == 'POST':
        user_form = UserRegistrationForm(request.POST)
        if user_form.is_valid():
            # Create a new user object but don't save yet
            new_user = user_form.save(commit=False)
            #Set the chosen password 
            new_user.set_password(
                user_form.cleaned_data['password']
            )
            #Save the User object
            new_user.save()
            # Create the user profile
            Profile.objects.create(user=new_user)
            create_actions(new_user, 'has created account') 

            context = {'new_user':new_user}
            return render(request, 'account/register_done.html', context)
        
    else:
        user_form= UserRegistrationForm()

    context = {'user_form':user_form}
    return render(request,'account/register.html', context ) 

@login_required
def edit(request):
    if request.method == "POST":
        user_form = UserEditForm(instance= request.user, data = request.POST )
        profile_form = ProfileEditForm(instance= request.user.profile, data= request.POST, files= request.FILES)

        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, 'Profile updated successfully')
        else:
            messages.error(request, 'Error updating your profile')
    
    else:
        user_form = UserEditForm(instance= request.user)
        profile_form = ProfileEditForm(instance= request.user.profile)
    
    context = {'user_form': user_form,'profile_form': profile_form}
    return render(request, 'account/edit.html', context)



@login_required
def user_list(request):
    users = User.objects.filter(is_active=True)
    return render(request,'account/user/list.html',{'section': 'people','users': users})

@login_required
def user_detail(request, username):
    user = get_object_or_404(User,username=username,is_active=True)
    return render(request,'account/user/detail.html',{'section': 'people','user': user})

@require_POST
@ajax_required
@login_required
def user_follow(request):
    user_id = request.POST.get('id')
    action = request.POST.get('action')
    if user_id and action:
        try:
            user = User.objects.get(id=user_id)
            if action == 'follow':
                Contact.objects.get_or_create(user_from = request.user, user_to = user)
                create_actions(request.user,'is now following', user)
            else:
                Contact.objects.filter(user_from = request.user, user_to = user).delete()
            return JsonResponse({'status':'ok'})
        except User.DoesNotExist:
            return JsonResponse({'status':'ko'})
    return JsonResponse({'status':'ko'})

