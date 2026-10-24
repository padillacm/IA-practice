---
instance_id: 08-ml-system-design@design
session_id: gold-mlsd-weak
stage: ml-system-design
variant: design
phase: vo1
role: mle
level: L5
lang: en
domain: recsys
time_scale: 1.0
budget_minutes: 60
---

### T1 · interviewer · t=00m

Hi, I am Elena Vasquez, a Staff ML Engineer. Today: design the system that builds a member's personalized homepage, the rows, the titles inside each row and their order, on TV, mobile and web. Take a minute to ask me whatever you need.

<meta>
question_id: mlsd-design-homepage-rows-01
phase: intro
</meta>

### T2 · candidate · t=03m

OK. I would build a neural network that predicts which movies the member will click on, trained on all the click data we have. Then we show the movies with the highest predicted probability.

### T3 · interviewer · t=05m

What metric do you optimize, and what scale and latency are we talking about?

<meta>
question_id: mlsd-design-homepage-rows-01
phase: main
</meta>

### T4 · candidate · t=08m

Accuracy of the click prediction, I think. Scale is big, so we use Spark and a big GPU cluster. Latency should be fast.

### T5 · interviewer · t=10m

Walk me through how a request is served and how the model gets its data.

<meta>
question_id: mlsd-design-homepage-rows-01
phase: main
</meta>

### T6 · candidate · t=16m

The app sends the request to the model, the model gets the user's history from the database, and it returns the top 10 movies. For training we split the logs randomly into train and test sets and retrain every month.

### T7 · interviewer · t=18m

How do you handle the fact that members only click on what you showed them?

<meta>
question_id: mlsd-design-homepage-rows-01
phase: main
hint: {id: h1, level: substantive, competency: modeling_choices}
</meta>

### T8 · candidate · t=23m

I am not sure. Maybe we add more data? Clicks are the positives and all the other movies in the catalog are negatives.

### T9 · interviewer · t=25m

What if the service is down? And how do you test the new model?

<meta>
question_id: mlsd-design-homepage-rows-01
phase: main
</meta>

### T10 · candidate · t=31m

We have servers in the cloud so they should not go down. To test it we look at the accuracy on the test set and if it is higher than the old one we deploy it. Honestly, the interviewer's question about the page layout is not something I have seen before.

### T11 · interviewer · t=34m

Thanks, we will stop here.

<meta>
question_id: mlsd-design-homepage-rows-01
phase: closed
</meta>
