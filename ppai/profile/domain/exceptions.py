class ProfileError(Exception):
    pass


class InvalidProfileDataError(ProfileError):
    pass


class OnboardingIncompleteError(ProfileError):
    pass
