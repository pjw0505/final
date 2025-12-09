# =======================================================
# app.py: 고전 예술 기록 및 멸실유산 발굴 에이전트
# =======================================================

import streamlit as st
from openai import OpenAI
import json
import os
import time # 시뮬레이션 지연용

# -------------------------------------------------------
# 1. 클라이언트 초기화 함수 (st.secrets 사용)
# -------------------------------------------------------

@st.cache_resource
def get_openai_client():
    """Streamlit Secrets에서 API 키를 읽어 OpenAI 클라이언트를 초기화합니다."""
    
    # st.secrets 객체에서 API 키 값을 가져옵니다.
    try:
        # 키를 가져와서 양쪽 공백이나 줄바꿈 문자를 확실히 제거합니다.
        # [secrets] 섹션 내 OPENAI_API_KEY 항목에 접근합니다.
        api_key = st.secrets["secrets"]["OPENAI_API_KEY"].strip()
    except KeyError:
        # Secrets 설정이 누락된 경우
        st.error("오류: Streamlit Secrets에 [secrets] 섹션 또는 OPENAI_API_KEY가 누락되었습니다.")
        st.stop()
        
    # 키 값이 유효한지 최종 확인
    if not api_key or not api_key.startswith("sk-"):
        st.error("오류: API 키 (OPENAI_API_KEY)의 값이 유효하지 않습니다. Secrets 설정을 확인해주세요.")
        st.stop()
        
    return OpenAI(api_key=api_key)

# -------------------------------------------------------
# 2. Tool 함수 정의 (MCP 기능, Mock API)
# -------------------------------------------------------

def get_heritage_text_record(location: str, structure_name: str) -> str:
    """
    특정 지역과 구조물의 이름으로 역사 기록 텍스트를 검색하는 Tool입니다.
    (실제로는 공공데이터포털 API를 호출해야 합니다.)
    """
    time.sleep(1) # 시뮬레이션 지연
    
    if "홍길동" in structure_name:
        return json.dumps({
            "status": "success",
            "search_term": structure_name,
            "text_record": "홍길동 작가는 1920년대 초 일본에서 유학했으며, 당시 파리 화단의 추상적 경향에 영향을 받았으나, 귀국 후 조선미술전람회에서 '조선의 풍경'을 테마로 한 실험적인 단색화(Monochrome)를 주로 선보였다. 초기에는 채색화도 병행했으나, 후기에는 캔버스에 마포를 사용한 물성 위주 작업에 집중했다.",
            "exhibition_count": 5
        })
    return json.dumps({"status": "error", "text_record": f"'{structure_name}'에 대한 상세 기록을 찾을 수 없습니다."})

def generate_visualization_data(data: str, visualization_type: str) -> str:
    """
    분석된 데이터를 기반으로 시각화 자료(JSON)를 생성하는 Tool입니다.
    (실제로는 데이터 프레임을 처리하고 Plotly JSON을 반환해야 합니다.)
    """
    time.sleep(1.5) # 시뮬레이션 지연
    
    if "단색화" in data and visualization_type == "timeline":
        # LLM이 분석한 내용을 시각화 JSON으로 변환했다고 가정
        return json.dumps({
            "status": "success",
            "visualization_type": "연표",
            "data": [
                {"year": 1920, "event": "일본 유학 및 서양 추상화 경향 접촉"},
                {"year": 1925, "event": "단색화 기법 실험 시작"},
                {"year": 1930, "event": "조선미술전람회에서 마포 질감 위주 작품 발표"},
                {"year": 1935, "event": "초기 채색화 활동 중단"}
            ]
        })
    return json.dumps({"status": "error", "message": "요청된 시각화 데이터를 생성할 수 없습니다."})

# -------------------------------------------------------
# 3. Tool 스키마 정의 및 딕셔너리
# -------------------------------------------------------

tools = [
    {
        "type": "function",
        "function": {
            "name": "get_heritage_text_record",
            "description": "작가나 유산의 이름으로 상세한 역사 기록 텍스트를 검색합니다.",
            "parameters": {"type": "object", "properties": {"location": {"type": "string"}, "structure_name": {"type": "string"}}, "required": ["structure_name"]},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "generate_visualization_data",
            "description": "제공된 분석 텍스트를 기반으로 연표(timeline)나 차트(chart) 형태의 시각화 JSON 데이터를 생성합니다.",
            "parameters": {"type": "object", "properties": {"data": {"type": "string", "description": "분석할 텍스트 기록 전체"}, "visualization_type": {"type": "string", "description": "원하는 시각화 형식 (연표, 차트 등)"}}, "required": ["data", "visualization_type"]},
        },
    },
]

available_functions = {
    "get_heritage_text_record": get_heritage_text_record,
    "generate_visualization_data": generate_visualization_data,
}


# -------------------------------------------------------
# 4. 핵심 에이전트 실행 함수 (MCP 로직)
# -------------------------------------------------------

def run_master_agent(user_prompt: str, location: str, structure_name: str, viz_type: str):
    
    client = get_openai_client() # 클라이언트 객체 가져오기
    messages = [{"role": "user", "content": user_prompt}]
    tool_results = {}
    
    st.info("AI 에이전트가 요청을 분석하고 Tool 호출 계획을 수립합니다.")
    
    for i in range(3): # 최대 3번의 Tool 호출 기회 부여
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            tools=tools,
            tool_choice="auto",
        )
        
        response_message = response.choices[0].message
        
        # 1. 최종 텍스트 결과가 나오면 루프 종료
        if not response_message.tool_calls:
            return response_message.content, tool_results
        
        # 2. Tool Call 실행
        messages.append(response_message)
        
        for tool_call in response_message.tool_calls:
            function_name = tool_call.function.name
            function_args = json.loads(tool_call.function.arguments)
            
            st.warning(f"STEP {i+1}: 🛠️ 에이전트가 Tool '{function_name}'을(를) 호출합니다.")
            
            # get_heritage_text_record 호출 시, UI 입력값 전달
            if function_name == "get_heritage_text_record":
                function_args['location'] = location
                function_args['structure_name'] = structure_name
            
            # generate_visualization_data 호출 시, 이전 검색 결과와 시각화 타입 전달
            elif function_name == "generate_visualization_data":
                record = tool_results.get("get_heritage_text_record", {}).get("text_record", "")
                function_args['data'] = record
                function_args['visualization_type'] = viz_type
            
            function_response = available_functions[function_name](**function_args)
            
            # 3. Tool 실행 결과를 저장하고 LLM에게 다시 전달 (Chain of Thought)
            tool_results[function_name] = json.loads(function_response)
            messages.append({"tool_call_id": tool_call.id, "role": "tool", "content": function_response})
            
    # 최종 응답 처리 (루프가 끝나도 최종 응답이 없을 경우)
    final_response = client.chat.completions.create(model="gpt-4o-mini", messages=messages)
    return final_response.choices[0].message.content, tool_results


# -------------------------------------------------------
# 5. Streamlit UI 및 실행 로직
# -------------------------------------------------------

st.title("📜 지역 문화유산 디지털 마스터 에이전트")
st.markdown("역사 기록을 분석하고 멸실된 유산의 배경을 시각화합니다.")

# 사이드바 (입력 영역)
with st.sidebar:
    st.header("문화유산 정보 입력")
    location = st.text_input("지역:", "서울 종로")
    structure_name = st.text_input("작가/유산 이름:", "홍길동 작가")
    
    viz_type = st.selectbox(
        "분석 시각화 형식:", 
        ['연표', '차트', '일반 분석']
    )
    
    prompt = st.text_area(
        "AI 분석 요청:", 
        f"'{structure_name}'의 역사 기록을 검색하고, 그 기록을 바탕으로 주요 활동 시기를 '{viz_type}' 형식으로 시각화할 수 있도록 분석해 줘.",
        height=150
    )

# 메인 실행 버튼
if st.button("🔎 분석 및 시각화 실행"): 
    if structure_name and prompt:
        with st.spinner("AI 에이전트가 기록 검색 및 시각화 명령을 진행 중입니다..."):
            
            # 6. run_master_agent 함수 호출
            analysis_text, tool_results = run_master_agent(prompt, location, structure_name, viz_type)
            
            # 7. 결과 출력
            st.subheader("💡 에이전트 최종 분석 및 스토리텔링")
            st.write(analysis_text)
            
            if "get_heritage_text_record" in tool_results:
                record = tool_results["get_heritage_text_record"]
                if record.get("status") == "success":
                    st.subheader("📜 검색된 원본 역사 기록")
                    st.code(record["text_record"], language='markdown')
            
            if "generate_visualization_data" in tool_results:
                viz_data = tool_results["generate_visualization_data"]
                if viz_data.get("status") == "success" and viz_data.get("visualization_type") == "연표":
                    st.subheader("📊 활동 연표 시각화 결과")
                    
                    # Mock 연표 데이터 Streamlit 테이블로 출력
                    df = st.dataframe(viz_data["data"], use_container_width=True)
                    st.markdown("_(실제 프로젝트에서는 Plotly/Altair를 사용하여 인터랙티브한 그래프를 여기에 표시할 수 있습니다.)_")

    else:
        st.warning("작가/유산 이름과 분석 요청을 입력해 주세요.")
