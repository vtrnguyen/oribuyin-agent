import os
import random
import importlib
from dotenv import load_dotenv
import openai
from app.db import get_connection

# ==== handle exception ====
RateLimitError = None
OpenAIError = None
try:
    openai_mod = importlib.import_module("openai")
    RateLimitError = getattr(openai_mod, "RateLimitError", None)
    OpenAIError = getattr(openai_mod, "OpenAIError", None)
    if RateLimitError is None or OpenAIError is None:
        error_mod = getattr(openai_mod, "error", None)
        if error_mod:
            RateLimitError = getattr(error_mod, "RateLimitError", RateLimitError)
            OpenAIError = getattr(error_mod, "OpenAIError", OpenAIError)
except Exception:
    RateLimitError = None
    OpenAIError = None

if RateLimitError is None:
    class RateLimitError(Exception):
        pass

if OpenAIError is None:
    class OpenAIError(Exception):
        pass


load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")


class LocalOpenAI:
    """Minimal adapter that provides an `invoke(prompt)` method similar to the langchain OpenAI wrapper.

    It uses the OpenAI Completion API (text-davinci-003 or gpt-3.5-turbo via ChatCompletion if desired).
    """
    def __init__(self, api_key: str = None, model: str = None):
        self.model = model or os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")

    def invoke(self, prompt: str):
        """Return the model's text response for a prompt.

        For gpt-3.5-turbo we use ChatCompletion, otherwise fallback to completions.
        """
        try:
            if "gpt-" in self.model or self.model.startswith("gpt-"):
                # use ChatCompletion
                resp = openai.ChatCompletion.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=512,
                    temperature=0.7,
                )
                # extract assistant content
                return resp["choices"][0]["message"]["content"].strip()
            else:
                resp = openai.Completion.create(
                    model=self.model,
                    prompt=prompt,
                    max_tokens=512,
                    temperature=0.7,
                )
                return resp["choices"][0]["text"].strip()
        except Exception:
            raise


llm = LocalOpenAI()


def ai_rephrase(base_text: str) -> str:
    """Dùng OpenAI để viết lại câu trả lời cho tự nhiên hơn"""
    try:
        prompt = (
            f"Hãy viết lại nội dung sau bằng tiếng Việt sao cho tự nhiên, thân thiện, "
            f"ngắn gọn và đúng ý chính:\n\n{base_text}"
        )
        result = llm.invoke(prompt)
        return result.strip()
    except Exception:
        return base_text


def handle_question(question: str):
    """Trả lời tự động dựa trên nội dung câu hỏi"""

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        q = question.lower()

        if "bán chạy" in q or "best seller" in q:
            cursor.execute("""
                SELECT p.name, p.image, SUM(oi.quantity) AS sold
                FROM order_items oi
                JOIN products p ON oi.product_id = p.id
                GROUP BY oi.product_id
                ORDER BY sold DESC
                LIMIT 5;
            """)
            data = cursor.fetchall()
            return {"type": "best_sellers", "data": data}

        elif "đánh giá cao" in q or "rating" in q or "nhiều sao" in q:
            cursor.execute("""
                SELECT p.name, p.image, AVG(r.rating) AS avg_rating
                FROM reviews r
                JOIN products p ON r.product_id = p.id
                GROUP BY r.product_id
                ORDER BY avg_rating DESC
                LIMIT 5;
            """)
            data = cursor.fetchall()
            return {"type": "high_rating", "data": data}

        elif "danh mục" in q or "category" in q:
            cursor.execute("""
                SELECT c.name, c.image, COUNT(oi.id) AS purchases
                FROM order_items oi
                JOIN products p ON oi.product_id = p.id
                JOIN categories c ON p.category_id = c.id
                GROUP BY c.id
                ORDER BY purchases DESC
                LIMIT 5;
            """)
            data = cursor.fetchall()
            return {"type": "categories", "data": data}

        elif "mua hàng" in q or "đặt hàng" in q or "mua sản phẩm" in q:
            responses = [
                "Bạn có thể mua hàng bằng cách thêm sản phẩm vào giỏ, sau đó thanh toán qua chuyển khoản hoặc COD. OriBuyin sẽ xác nhận đơn qua email hoặc số điện thoại.",
                "Để mua hàng tại OriBuyin, bạn chỉ cần chọn sản phẩm, thêm vào giỏ hàng rồi tiến hành thanh toán. Chúng tôi hỗ trợ chuyển khoản và COD.",
                "Mua hàng tại OriBuyin rất đơn giản! Thêm sản phẩm vào giỏ hoặc chọn 'Mua ngay', sau đó chọn phương thức thanh toán phù hợp với bạn."
            ]
            base_msg = random.choice(responses)
            if random.random() < 0.2:
                base_msg = ai_rephrase(base_msg)
            return {"type": "order_process", "data": base_msg}

        elif "thanh toán" in q or "payment" in q:
            responses = [
                "OriBuyin hỗ trợ hai hình thức thanh toán: chuyển khoản ngân hàng hoặc COD (thanh toán khi nhận hàng).",
                "Bạn có thể thanh toán bằng chuyển khoản hoặc trả tiền mặt khi nhận hàng.",
                "Chúng tôi hỗ trợ hai phương thức thanh toán linh hoạt: chuyển khoản trực tiếp hoặc thanh toán khi nhận hàng (COD)."
            ]
            msg = random.choice(responses)
            if random.random() < 0.2:
                msg = ai_rephrase(msg)
            return {"type": "payment_info", "data": msg}

        elif "giao hàng" in q or "ship" in q or "vận chuyển" in q:
            responses = [
                "OriBuyin giao hàng toàn quốc qua GHTK và Viettel Post. Thời gian từ 2–5 ngày tùy khu vực.",
                "Chúng tôi giao hàng nhanh trên toàn quốc thông qua các đơn vị vận chuyển uy tín. Bạn có thể theo dõi trạng thái đơn hàng trong mục 'Đơn hàng của tôi'.",
                "OriBuyin hợp tác với GHTK và Viettel Post để giao hàng trong 2–5 ngày làm việc."
            ]
            msg = random.choice(responses)
            if random.random() < 0.2:
                msg = ai_rephrase(msg)
            return {"type": "shipping_info", "data": msg}

        elif "đổi hàng" in q or "trả hàng" in q or "hoàn hàng" in q:
            responses = [
                "OriBuyin hỗ trợ đổi hoặc trả hàng trong 7 ngày nếu sản phẩm còn nguyên tem mác, chưa sử dụng.",
                "Bạn có thể yêu cầu đổi/trả hàng trong vòng 7 ngày kể từ khi nhận sản phẩm, miễn là hàng còn nguyên trạng.",
                "Nếu sản phẩm không đúng mong đợi, bạn có thể gửi yêu cầu đổi hoặc trả trong 7 ngày tại mục 'Hỗ trợ khách hàng'."
            ]
            msg = random.choice(responses)
            if random.random() < 0.2:
                msg = ai_rephrase(msg)
            return {"type": "return_policy", "data": msg}

        else:
            fallback = (
                "Xin lỗi, hiện tại tôi chưa có câu trả lời cho câu hỏi này. "
                "Bạn có thể liên hệ bộ phận hỗ trợ OriBuyin để được giúp đỡ nhanh hơn."
            )
            if random.random() < 0.2:
                fallback = ai_rephrase(fallback)
            return {"type": "ai_general", "data": fallback}

    finally:
        try:
            cursor.close()
        except Exception:
            pass
        try:
            conn.close()
        except Exception:
            pass
