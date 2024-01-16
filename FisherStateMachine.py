import sys, time
from Controller import ActionController

from State import InitializationFisherState


class FisherStateMachine():
    def __init__(self,action):
        self.action = action
        self.state = InitializationFisherState(action=self.action)

    def update(self, sense):
        result = self.state.update(sense)
        if result:
            self.state = result
