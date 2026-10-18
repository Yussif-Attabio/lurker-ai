"""Minimal drop-in factory; supply your own local or remote Decider adapter."""

from typing import Any
from strands import Agent

from decision_pattern import ChimeInGate
from decision_pattern.strands_hook import ChimeInIntervention


def build_agent(adapter: Any) -> tuple[Agent, ChimeInIntervention]:
    gate = ChimeInGate(adapter, reply_threshold=0.20, react_threshold=0.04, k=3)
    intervention = ChimeInIntervention(gate)
    return Agent(interventions=[intervention]), intervention


if __name__ == "__main__":
    print("Import build_agent and pass an adapter with decide(state, question, options).")
