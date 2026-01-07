import os
import json
import requests
from datetime import datetime
from pathlib import Path
from flask import Flask, request, jsonify

app = Flask(__name__)

# 설정
DATA_DIR = Path(__file__).parent / "data"
USERS_FILE = DATA_DIR / "users.json"


def load_users() -> dict:
    """저장된 유저 데이터 불러오기 (카카오 user_id -> boj_id 매핑)"""
    DATA_DIR.mkdir(exist_ok=True)
    if USERS_FILE.exists():
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_users(users: dict):
    """유저 데이터 저장"""
    DATA_DIR.mkdir(exist_ok=True)
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=2)


def get_solved_count(boj_id: str) -> dict | None:
    """solved.ac API로 유저 정보 가져오기"""
    url = f"https://solved.ac/api/v3/user/show?handle={boj_id}"

    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return {
                "solvedCount": data.get("solvedCount", 0),
                "tier": data.get("tier", 0),
            }
        elif response.status_code == 404:
            return None
    except Exception as e:
        print(f"API 에러: {e}")
        return None
    return None


def get_tier_name(tier: int) -> str:
    """티어 숫자를 이름으로 변환"""
    tiers = ["Unrated", "Bronze V", "Bronze IV", "Bronze III", "Bronze II", "Bronze I",
             "Silver V", "Silver IV", "Silver III", "Silver II", "Silver I",
             "Gold V", "Gold IV", "Gold III", "Gold II", "Gold I",
             "Platinum V", "Platinum IV", "Platinum III", "Platinum II", "Platinum I",
             "Diamond V", "Diamond IV", "Diamond III", "Diamond II", "Diamond I",
             "Ruby V", "Ruby IV", "Ruby III", "Ruby II", "Ruby I", "Master"]
    return tiers[tier] if 0 <= tier < len(tiers) else "Unknown"


def kakao_response(text: str):
    """카카오 챗봇 응답 형식"""
    return jsonify({
        "version": "2.0",
        "template": {
            "outputs": [
                {
                    "simpleText": {
                        "text": text
                    }
                }
            ]
        }
    })


@app.route("/")
def home():
    return "BOJ 인증 봇 서버가 실행 중입니다!"


@app.route("/kakao/register", methods=["POST"])
def kakao_register():
    """카카오 챗봇 - 유저 등록"""
    try:
        data = request.json

        # 카카오 유저 ID
        kakao_user_id = data["userRequest"]["user"]["id"]

        # 파라미터에서 백준 ID 추출
        boj_id = data["action"]["params"].get("boj_id", "").strip()

        if not boj_id:
            return kakao_response("백준 아이디를 입력해주세요.\n사용법: 등록 백준아이디")

        # solved.ac에서 유저 확인
        solved_data = get_solved_count(boj_id)
        if solved_data is None:
            return kakao_response(f"'{boj_id}'를 찾을 수 없어요.\n백준 아이디를 확인해주세요.")

        # 유저 데이터 로드
        users = load_users()

        # 이미 등록된 경우 업데이트
        if kakao_user_id in users:
            old_boj_id = users[kakao_user_id]["boj_id"]
            if old_boj_id == boj_id:
                message = f"이미 '{boj_id}'로 등록되어 있어요!"
            else:
                message = f"백준 아이디를 '{old_boj_id}'에서 '{boj_id}'로 변경했어요!"
        else:
            message = "등록 완료!"

        # 저장
        users[kakao_user_id] = {
            "boj_id": boj_id,
            "solved_count": solved_data["solvedCount"],
            "registered_at": datetime.now().isoformat(),
            "last_checked": datetime.now().isoformat(),
        }
        save_users(users)

        tier_name = get_tier_name(solved_data["tier"])

        response_text = (
            f"{message}\n"
            f"━━━━━━━━━━━━━━━\n"
            f"👤 백준 ID: {boj_id}\n"
            f"🏆 티어: {tier_name}\n"
            f"✅ 현재 푼 문제: {solved_data['solvedCount']}문제"
        )

        return kakao_response(response_text)

    except Exception as e:
        print(f"등록 에러: {e}")
        return kakao_response("등록 중 오류가 발생했어요. 다시 시도해주세요.")


@app.route("/kakao/status", methods=["POST"])
def kakao_status():
    """카카오 챗봇 - 현황 확인"""
    try:
        users = load_users()

        if not users:
            return kakao_response("등록된 유저가 없어요.\n'등록 백준아이디' 명령어로 먼저 등록해주세요!")

        results = []
        success_count = 0
        today = datetime.now().strftime("%Y-%m-%d")

        for kakao_user_id, user in users.items():
            boj_id = user["boj_id"]
            last_count = user.get("solved_count", 0)

            # solved.ac에서 현재 정보 가져오기
            data = get_solved_count(boj_id)
            if data is None:
                results.append(f"⚠️ {boj_id}: 조회 실패")
                continue

            current_count = data["solvedCount"]
            diff = current_count - last_count

            if diff > 0:
                results.append(f"✅ {boj_id}: +{diff}문제")
                success_count += 1
            else:
                results.append(f"❌ {boj_id}: 0문제")

            # 카운트 업데이트 (다음 확인을 위해)
            users[kakao_user_id]["solved_count"] = current_count
            users[kakao_user_id]["last_checked"] = datetime.now().isoformat()

        # 업데이트된 데이터 저장
        save_users(users)

        total = len(users)
        message = (
            f"📊 {today} 일일 인증 현황\n"
            f"━━━━━━━━━━━━━━━\n"
            + "\n".join(results)
            + f"\n━━━━━━━━━━━━━━━\n"
            + f"🎯 {success_count}/{total}명 인증 완료!"
        )

        return kakao_response(message)

    except Exception as e:
        print(f"현황 확인 에러: {e}")
        return kakao_response("현황 확인 중 오류가 발생했어요. 다시 시도해주세요.")


@app.route("/health", methods=["GET"])
def health():
    """헬스체크 엔드포인트"""
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
