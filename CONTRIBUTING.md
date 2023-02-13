# Contributing to Donkeycar

Thank you for contributing to the Donkeycar project.  Here are some guidelines that can help you be successful in getting your contributions merged into Donkeycar.

## What makes for a good Pull Request?
- The code implements a bug fix or optimization/refactor to a preexisting feature or adds a new feature.
- If the code is adding a new feature, it would be advisable to open an Issue in the Donkeycar repo prior to opening the PR.  This would allow discussion on how the feature may be best implemented and even if the feature is something that would get accepted into Donkeycar.  The new feature should have fairly broad applicability; it should be a feature that would be useful to a lot of users.
- The code should be well writte have some comments in it where it is not obvious what is going on and why. It should also be pep-8 compliant in style. Like with any other code, it should avoid code duplications from itself or other existing code. It should keep data and methods arranged in classes as much as possible and should avoid lengthy, monolithic functions and functions with too many input/output parameters. Monkey-patching is a no-go and pythonic style usually is a good guide.
- The code must work on our currently supported platforms; Raspberry Pi OS and the Jetson Nano for cars and Linux, Mac and WSL on Windows.
- The code should have unit tests.
- The code should work on the version of Python specified in the installation documentation at docs.donkeycar.com
- The PR should include instructions/steps telling how the feature/fix can be tested by a person.  In some cases you may want to create a video and link it from Youtube or Vimeo to show the process; for instance if it includes mounting hardware.
- For new features or changes to preexisting feature you should also open a PR in the documentation repo https://github.com/autorope/donkeydocs with updated docs.  A human tester will want to refer to that when testing.


## What makes for a Pull Request that is not likely to get accepted?
- It adds a feature that is not useful to a broad audience or is too complex/complicated for the Donkeycar audience.  For instance, it adds a driver for a custom piece of hardware or a piece of hardware that is not generally obtainable.  In this case we will encourage you to maintain the feature in your own fork on Donkeycar and keep that fork up to date with the main branch.
- It does not have unit tests.
- The PR is opened and it receives comments and/or requests for change, but no response is made by the owner of the PR.  In this case we will eventually close the PR as unresponsive.


## Pull Request Process
- Fork the Donkeycar repository into your own github account.  See [About Forks](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/working-with-forks/about-forks) in the github docs.
- Create a branch based off the `main` branch in your repository and make the changes.  
- Open a pull request to the Donkeycar main repository.  If it is associated with a github issue then reference the issue in the pull request.  See [Creating a Pull Request from a Fork](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/proposing-changes-to-your-work-with-pull-requests/creating-a-pull-request-from-a-fork) in the github docs.
  - If the PR is associated with an Issue then link the issue in the PR description.
  - If the PR is associated with a documentation change then link to the associated PR in the documentation repo.
- The maintainers will be automatically notified of the pull request.  
- Maintainers will provide comments and/or request for changes in the PR.  This could take a little while; we have a small volunteer team that is working on a number of initiatives.  You can get more visibility by announcing the PR in the software channel on the Discord.
- The owner of the PR should be checking it for comments and/or request for changes and responding.  In particular, if there are requests for changes but you cannot get to them reasonably quickly then add a comment in the PR that helps us understand your timeframe so that we don't close that PR as unresponsive.
- There is a possibility that we choose to not move forward with the PR and it will be closed.  You can minimize that chance by discussing the feature or fix in an Issue prior to opening a PR (see above).
- If once all requested changes are made then the PR can be accepted.  At this point one of the maintainers will merge the PR and the PR will be closed as completed.  Congratulations, you just made the world better.

