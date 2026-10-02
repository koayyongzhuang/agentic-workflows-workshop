from langchain_core.messages import HumanMessage

from workshop.mock_llm import MockChatModel, extract_args
from workshop.tools import ALL_TOOLS


def test_selects_eligibility_tool_with_args():
    llm = MockChatModel().bind_tools(list(ALL_TOOLS.values()))
    msg = llm.invoke([HumanMessage("Am I eligible for the Senior Mobility Grant? I'm 67, citizen, income $2,400 for 2 people")])
    call = msg.tool_calls[0]
    assert call["name"] == "check_eligibility"
    assert call["args"]["age"] == 67
    assert call["args"]["monthly_household_income"] == 2400
    assert call["args"]["household_size"] == 2
    assert call["args"]["scheme"] == "Senior Mobility Grant"


def test_count_params_do_not_steal_amounts():
    params = ALL_TOOLS["check_eligibility"].tool_call_schema.model_json_schema()
    args = extract_args(params, "I'm 70 and our household income is $3,000")
    assert "household_size" not in args and args["monthly_household_income"] == 3000
