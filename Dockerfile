# ----------------------------
# 1. 베이스 이미지
# ----------------------------
FROM python:3.12-slim

# ----------------------------
# 2. 환경 변수
# ----------------------------
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PATH="/root/.local/bin:/root/.cargo/bin:${PATH}"

# ----------------------------
# 3. 필수 패키지 설치
# ----------------------------
RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    libpq-dev \
    netcat-openbsd \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# ----------------------------
# 4. uv 설치 (선택)
# ----------------------------
RUN curl -LsSf https://astral.sh/uv/install.sh | sh

# ----------------------------
# 5. 작업 디렉토리 설정
# ----------------------------
WORKDIR /last-AWS

# ----------------------------
# 6. 의존성 파일 복사 및 설치
# ----------------------------
COPY ./requirements.txt ./
RUN uv pip install --system --no-cache-dir -r requirements.txt

# ----------------------------
# 7. 애플리케이션 코드 복사
# ----------------------------
COPY ./manage.py ./
COPY ./apps ./apps
COPY ./settings ./settings

# ----------------------------
# 8. 스크립트 복사 및 권한 설정
# ----------------------------
COPY ./scripts ./scripts
RUN chmod +x ./scripts/run.sh

# ----------------------------
# 9. 포트 개방
# ----------------------------
EXPOSE 8000

# ----------------------------
# 10. 컨테이너 시작 시 run.sh 실행
# ----------------------------
CMD ["/bin/bash", "./scripts/run.sh"]
