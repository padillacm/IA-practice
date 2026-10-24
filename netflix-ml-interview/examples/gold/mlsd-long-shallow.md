---
instance_id: 08-ml-system-design@design
session_id: gold-mlsd-long-shallow
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

### T2 · candidate · t=05m

Great question, thank you, and I really appreciate the opportunity to discuss this fascinating problem. Personalization is a very important topic and it is crucial to think holistically about the end-to-end member experience. I believe that in order to design this system properly we need to consider many different aspects, such as the business objectives, the user needs, the technical constraints, the data, the models, the infrastructure, and of course the metrics. The goal is to maximize member satisfaction and engagement in a scalable, robust and flexible way, leveraging state of the art techniques across the whole stack. There are many stakeholders and many trade-offs, and a good design always balances them carefully. I would work closely with product, data and engineering to make sure everything is aligned, and I would iterate quickly.

### T3 · interviewer · t=08m

Can you commit to a metric and some numbers for scale and latency?

<meta>
question_id: mlsd-design-homepage-rows-01
phase: main
</meta>

### T4 · candidate · t=13m

Absolutely. Metrics are very important, and I would use a rich set of metrics, including engagement, satisfaction, retention, diversity, relevance, and others, depending on the needs of the business. Scale would be large, as Netflix is a global service, and latency would need to be low to provide a great experience. We would of course consider both, and the right numbers would be defined together with the stakeholders as the project evolves.

### T5 · interviewer · t=15m

Walk me through the architecture.

<meta>
question_id: mlsd-design-homepage-rows-01
phase: main
</meta>

### T6 · candidate · t=22m

The architecture would be modern, cloud-native, microservice-based and scalable. We would use a data lake, streaming, batch processing, a feature store, a model registry, a serving layer, caching, a CDN, load balancers and monitoring, all orchestrated with Kubernetes. Data flows from the sources through the pipelines into the models and then to the application layer, so that the member receives recommendations that are relevant and timely. Each component would be designed with best practices for reliability and security in mind, and we would use the best tools for each job.

### T7 · interviewer · t=24m

Which model, loss and training data?

<meta>
question_id: mlsd-design-homepage-rows-01
phase: main
</meta>

### T8 · candidate · t=31m

We would use state of the art deep learning, like transformers, possibly with attention, embeddings and multi-task learning, and potentially large language models, together with classical methods such as matrix factorization and gradient boosting as baselines, in an ensemble. Training would use large amounts of high quality data and careful hyperparameter tuning, with regularization to avoid overfitting. We would continuously improve the models as we learn from the data, because data is the key to everything in machine learning.

### T9 · interviewer · t=33m

How do you handle failures, and how do you validate online?

<meta>
question_id: mlsd-design-homepage-rows-01
phase: main
</meta>

### T10 · candidate · t=42m

For failures we would have redundancy, fault tolerance, graceful degradation and monitoring and alerting, following SRE best practices, so that the system is highly available. For validation we would run experiments, A/B tests and analyze the results with statistical rigor, and monitor the key metrics so that we can iterate. Overall, I think a strong collaborative culture and a data-driven mindset are the most important ingredients, and I am confident that with a great team we can build something amazing.

### T11 · interviewer · t=46m

Thank you. That is our time.

<meta>
question_id: mlsd-design-homepage-rows-01
phase: closed
</meta>
