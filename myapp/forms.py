import uuid
from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.forms import PasswordChangeForm

from .models import UserInfo


class LoginForm(forms.Form):
    username = forms.CharField(label="用户名", max_length=150)
    password = forms.CharField(label="密码", widget=forms.PasswordInput)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].widget.attrs.update({"class": "form-control"})
        self.fields["password"].widget.attrs.update({"class": "form-control"})

    def clean(self):
        cleaned_data = super().clean()
        username = cleaned_data.get("username")
        password = cleaned_data.get("password")
        if username and password:
            user = authenticate(username=username, password=password)
            if not user:
                raise forms.ValidationError("用户名或密码错误")
            cleaned_data["user"] = user
        return cleaned_data


class RegistrationForm(forms.ModelForm):
    password1 = forms.CharField(label="密码", widget=forms.PasswordInput)
    password2 = forms.CharField(label="确认密码", widget=forms.PasswordInput)

    class Meta:
        model = UserInfo
        fields = ["username", "email", "nickname", "sex", "age"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        widgets_map = {
            "username": "form-control",
            "email": "form-control",
            "nickname": "form-control",
            "sex": "form-select",
            "age": "form-control",
            "password1": "form-control",
            "password2": "form-control",
        }
        for name, css in widgets_map.items():
            if name in self.fields:
                self.fields[name].widget.attrs.update({"class": css})

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("两次密码输入不一致")
        return password2

    def clean_username(self):
        username = self.cleaned_data["username"]
        if UserInfo.objects.filter(username=username).exists():
            raise forms.ValidationError("用户名已存在")
        return username

    def clean_email(self):
        email = self.cleaned_data["email"]
        if UserInfo.objects.filter(email=email).exists():
            raise forms.ValidationError("邮箱已被注册")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.user_ID = uuid.uuid4().hex
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user


class ProfileForm(forms.ModelForm):
    class Meta:
        model = UserInfo
        fields = ["username", "nickname", "email", "sex", "age"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        widgets_map = {
            "username": "form-control",
            "nickname": "form-control",
            "email": "form-control",
            "sex": "form-select",
            "age": "form-control",
        }
        for name, css in widgets_map.items():
            if name in self.fields:
                self.fields[name].widget.attrs.update({"class": css})

    def clean_username(self):
        username = self.cleaned_data.get("username")
        if username:
            # 检查用户名是否已被其他用户使用（排除当前用户）
            existing_user = UserInfo.objects.filter(username=username).exclude(pk=self.instance.pk).first()
            if existing_user:
                raise forms.ValidationError("该用户名已被使用，请选择其他用户名")
        return username

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if email:
            # 检查邮箱是否已被其他用户使用（排除当前用户）
            existing_user = UserInfo.objects.filter(email=email).exclude(pk=self.instance.pk).first()
            if existing_user:
                raise forms.ValidationError("该邮箱已被注册，请使用其他邮箱")
        return email


class PasswordUpdateForm(PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in self.fields:
            self.fields[name].widget.attrs.update({"class": "form-control"})

