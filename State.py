from abc import ABC, abstractmethod
import time


CASTING_COOLDOWN = 1
WAITING_COOLDOWN = 0.5
REELING_IN_COOLDOWN = 0.5


class FisherStateAbstract(ABC):
    def __init__(self, code, description, action):
        self.code = code
        self.description = description
        self.action = action

    @abstractmethod
    def update(self, sense):
        pass


class InitializationFisherState(FisherStateAbstract):

    def __init__(self, action):
        super().__init__(code="INIT", description="Waiting for user...", action=action)

    def update(self, sense):
        if sense > 1:
            return CastingFisherState(cast=False, action=self.action)
        else:
            return None


class CastingFisherState(FisherStateAbstract):
    def __init__(self, action, cast=True):
        super().__init__(code="CAST", description="Casting the line", action=action)
        self.created_at = time.time()
        if cast:
            self.action()

    def update(self, sense):
        if (time.time() - self.created_at) > CASTING_COOLDOWN and sense < 1:
            return WaitingFisherState(action=self.action)
        else:
            return None


class WaitingFisherState(FisherStateAbstract):
    def __init__(self, action):
        super().__init__(code="WAIT", description="Waiting for movement", action=action)
        self.created_at = time.time()

    def update(self, sense):
        if (time.time() - self.created_at) > WAITING_COOLDOWN and sense > 1:
            return ReelingInFisherState(action=self.action)
        else:
            return None


class ReelingInFisherState(FisherStateAbstract):
    def __init__(self, action):
        super().__init__(code="REEL", description="Hooked - reeling in", action=action)
        self.created_at = time.time()
        self.action()

    def update(self, sense):
        if (time.time() - self.created_at) > REELING_IN_COOLDOWN and sense < 1:
            return CastingFisherState(action=self.action)
        else:
            return None
