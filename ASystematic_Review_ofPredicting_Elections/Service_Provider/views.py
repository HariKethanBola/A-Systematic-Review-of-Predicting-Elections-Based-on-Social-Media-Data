from django.shortcuts import render, redirect
from django.db.models import Count, Avg, Q
from django.http import HttpResponse
import xlwt
import pandas as pd
import os

from nltk import bigrams
from nltk.corpus import stopwords
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from collections import Counter

from Remote_User.models import (
    ClientRegister_Model,
    Election_model,
    Election_prediction_model,
    detection_ratio_model
)

# ---------------- SERVICE PROVIDER LOGIN ---------------- #

def serviceproviderlogin(request):
    if request.method == "POST":
        admin = request.POST.get('username')
        password = request.POST.get('password')

        if (admin == "Admin" and password == "Admin") or (admin == "hari" and password == "hari143"):
            return redirect('View_Remote_Users')
        else:
            return render(
                request,
                'SProvider/serviceproviderlogin.html',
                {'error': 'Invalid credentials'}
            )

    return render(request, 'SProvider/serviceproviderlogin.html')




# ---------------- VIEW REMOTE USERS ---------------- #

def View_Remote_Users(request):
    obj = ClientRegister_Model.objects.all()
    return render(request, 'SProvider/View_Remote_Users.html', {'objects': obj})


# ---------------- TRENDING TOPICS ---------------- #

def ViewTrendings(request):
    topic = Election_prediction_model.objects.values(
        'prediction'
    ).annotate(dcount=Count('prediction')).order_by('-dcount')

    return render(request, 'SProvider/ViewTrendings.html', {'objects': topic})


# ---------------- CHARTS ---------------- #

def charts(request, chart_type):
    chart1 = detection_ratio_model.objects.values(
        'names'
    ).annotate(dcount=Avg('ratio'))

    return render(request, "SProvider/charts.html", {
        'form': chart1,
        'chart_type': chart_type
    })


def charts1(request, chart_type):
    chart1 = detection_ratio_model.objects.values(
        'names'
    ).annotate(dcount=Avg('ratio'))

    return render(request, "SProvider/charts1.html", {
        'form': chart1,
        'chart_type': chart_type
    })


def likeschart(request, like_chart):
    charts = detection_ratio_model.objects.values(
        'names'
    ).annotate(dcount=Avg('ratio'))

    return render(request, "SProvider/likeschart.html", {
        'form': charts,
        'like_chart': like_chart
    })


# ---------------- PREDICTION RESULT ---------------- #

def View_Election_Tweet_Predicted_Type(request):
    obj = Election_prediction_model.objects.all()
    return render(
        request,
        'SProvider/View_Election_Tweet_Predicted_Type.html',
        {'list_objects': obj}
    )


# ---------------- DOWNLOAD EXCEL ---------------- #

def Download_Trained_DataSets(request):
    response = HttpResponse(content_type='application/ms-excel')
    response['Content-Disposition'] = 'attachment; filename="Election_Predictions_Results.xls"'

    wb = xlwt.Workbook(encoding='utf-8')
    ws = wb.add_sheet("Predictions")

    font_style = xlwt.XFStyle()
    font_style.font.bold = True

    headers = ['Tweeter', 'Total Tweet Time', 'Tweet', 'Prediction']
    for col, header in enumerate(headers):
        ws.write(0, col, header, font_style)

    row = 1
    for obj in Election_prediction_model.objects.all():
        ws.write(row, 0, obj.tweeter)
        ws.write(row, 1, obj.total_tweet_Time)
        ws.write(row, 2, obj.tweet)
        ws.write(row, 3, obj.prediction)
        row += 1

    wb.save(response)
    return response


# ---------------- TRAIN MODEL ---------------- #

def train_model(request):
    detection_ratio_model.objects.all().delete()

    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    csv_path = os.path.join(BASE_DIR, 'US_election_2020_Tweets.csv')

    df = pd.read_csv(csv_path)

    df_CW = df[df.Tweeted_about == 'Chris Wallace']
    df_JB = df[df.Tweeted_about == 'Vice President Joe Biden']
    df_DT = df[df.Tweeted_about == 'President Donald J. Trump']

    text_CW = " ".join(df_CW.text)
    text_JB = " ".join(df_JB.text)
    text_DT = " ".join(df_DT.text)

    sia = SentimentIntensityAnalyzer()

    sent_CW = sia.polarity_scores(text_CW)
    sent_DT = sia.polarity_scores(text_DT)
    sent_JB = sia.polarity_scores(text_JB)

    Election_prediction_model.objects.all().delete()

    for t in Election_model.objects.all():
        sentiment = sia.polarity_scores(t.tweet)['compound']

        if sentiment >= 0.05:
            result = "Positive"
        elif sentiment <= -0.05:
            result = "Negative"
        else:
            result = "Neutral"

        Election_prediction_model.objects.create(
            tweeter=t.tweeter,
            total_tweet_Time=t.total_tweet_Time,
            tweet=t.tweet,
            prediction=result
        )

    total = Election_prediction_model.objects.count()

    for label in ['Positive', 'Negative', 'Neutral']:
        count = Election_prediction_model.objects.filter(prediction=label).count()
        if total > 0:
            ratio = (count / total) * 100
            detection_ratio_model.objects.create(names=label, ratio=ratio)

    obj = detection_ratio_model.objects.all()

    return render(request, 'SProvider/train_model.html', {
        'objs': obj,
        'CW': sent_CW,
        'DT': sent_DT,
        'JB': sent_JB
    })
