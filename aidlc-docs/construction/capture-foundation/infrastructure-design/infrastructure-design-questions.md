# Infrastructure Design — Preguntas de Clarificación — UOW-01 Capture Foundation

La mayoría de la infraestructura ya se definió en NFR Design. Estas preguntas cubren decisiones concretas de deployment que faltan.

---

## Question 1
¿En qué región de AWS quieres desplegar?

A) us-east-1 (N. Virginia — más servicios disponibles, menor costo general)
B) us-west-2 (Oregon)
C) eu-west-1 (Ireland)
D) sa-east-1 (São Paulo — menor latencia si estás en Latam)
X) Other (please describe after [Answer]: tag below)

[Answer]: A

---

## Question 2
¿Cómo quieres exponer el endpoint HTTPS para el webhook de Telegram? Telegram requiere una URL pública con TLS válido.

A) ALB + dominio custom que ya tengo (yo proveo el dominio, se usa ACM para certificado)
B) ALB + dominio nuevo que quiero registrar en Route 53
C) API Gateway (HTTP API) como frontal — maneja TLS automáticamente, sin necesidad de dominio custom (usa el URL generado por API Gateway)
X) Other (please describe after [Answer]: tag below)

[Answer]: C

---

## Question 3
¿Qué estrategia de environments quieres para el MVP?

A) Solo producción — un solo environment, despliego directo
B) Dev + Prod — dos environments separados (Terraform workspaces o carpetas)
C) Dev + Staging + Prod — tres environments
X) Other (please describe after [Answer]: tag below)

[Answer]: A

---

## Question 4
¿Dónde almacenar las imágenes Docker del bot?

A) Amazon ECR (Elastic Container Registry) — integración nativa con ECS
B) Docker Hub (público o privado)
X) Other (please describe after [Answer]: tag below)

[Answer]: A

---

## Question 5
¿Cómo quieres manejar el proceso de deployment (build + push imagen + terraform apply)?

A) Manual — build local, push a ECR, terraform apply desde mi máquina
B) Semi-automático — GitHub Actions (o similar) para build+push imagen, terraform apply manual
C) Automatizado — CI/CD completo (GitHub Actions) para build, push, terraform plan/apply en PR merge
X) Other (please describe after [Answer]: tag below)

[Answer]: B
