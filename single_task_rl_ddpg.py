from rlbench.environment import Environment
from rlbench.action_modes import ArmActionMode, ActionMode
from rlbench.observation_config import ObservationConfig
from rlbench.tasks import ReachTarget
import numpy as np
from collections import deque
import random
import matplotlib.pyplot as plt

from ddpg_agent import Agent
from config import *
from rlbench_env import RLBenchEnv


def ddpg(n_episodes=100,
         eps_start=1.0, eps_decay=1e-5, eps_end=0.05,
         max_t=1000, learn_every_step=100):
    scores_deque = deque(maxlen=100)
    scores, actor_losses, critic_losses = [], [], []
    eps = eps_start
    for i_episode in range(1, 1 + n_episodes):
        # _, obs = task.reset()
        # states = np.hstack((obs.joint_positions, obs.joint_velocities, obs.joint_forces))
        state = env.reset()
        # states = states[np.newaxis, :]
        agent.reset()

        avg_score, rewards = 0, []
        actor_loss_list, critic_loss_list = [], []
        for t in range(max_t):
            ## print(f"Step: {t}")
            actions = agent.act(state, add_noise=random.random() < eps)
            eps = max(eps - eps_decay, eps_end)

            # obs, reward, terminate = task.step(actions.ravel())
            # next_state = np.hstack((obs.joint_positions, obs.joint_velocities, obs.joint_forces))
            action = actions.ravel()
            next_state, reward, terminate, _ = env.step(action)
            if terminate:
                reward_bonus = (max_t - t) / max_t  # the faster the better!
                reward += reward_bonus
            # next_states = next_state[np.newaxis, :]
            # next_states = [next_state]
            done = 1. if terminate else 0.

            agent.step(state, actions, reward, next_state, done)

            # Learn, if enough samples are available in memory
            if len(agent.memory) > agent.batch_size and \
                    t % learn_every_step == 0:
                for _ in range(3):
                    experiences = agent.memory.sample(batch_size=agent.batch_size)
                    actor_loss, critic_loss = agent.learn(experiences, agent.gamma)
                    actor_loss_list.append(actor_loss)
                    critic_loss_list.append(critic_loss)

            rewards.append(reward)
            state = next_state
            if done:
                break
        avg_score = np.mean(rewards) if rewards else 0.
        scores_deque.append(avg_score)
        scores.append(avg_score)
        actor_losses.append(np.mean(actor_loss_list) if actor_loss_list else 0.)
        critic_losses.append(np.mean(critic_loss_list) if critic_loss_list else 0.)
        print(f"\rEpisode {i_episode}\tExploration: {eps:.6f}\t"
              f"Average Score: {np.mean(scores_deque):.2f}\tCurrent Score: {avg_score:.2f}\t"
              f"Actor Loss: {np.mean(actor_loss_list) if actor_loss_list else 0:.2e}"
              f"\tCritic Loss: {np.mean(critic_loss_list) if critic_loss_list else 0.:.2e}")

        if i_episode % 100 == 0:
            # agent.save()
            print('\rEpisode {}\tAverage Score: {:.2f}'.format(i_episode, np.mean(scores_deque)))

        if i_episode % 50 == 0:
            agent.save()
            print('Save Model\n\rEpisode {}\tAverage Score: {:.2f}'.format(i_episode, np.mean(scores_deque)))

    return scores, actor_losses, critic_losses


obs_config = ObservationConfig()
obs_config.set_all(False)
obs_config.joint_velocities = True
obs_config.joint_forces = True
obs_config.joint_positions = True

action_mode = ActionMode(ArmActionMode.ABS_JOINT_TORQUE)
env = RLBenchEnv("ReachTarget",
                 state_type_list=[
                     "joint_positions",
                     "joint_velocities",
                     # 'left_shoulder_rgb',
                     # 'right_shoulder_rgb',
                     'task_low_dim_state',
                 ])
state = env.reset()
action_dim = env.action_space.shape[0]
state_space = env.observation_space

agent = Agent(state_space, HIDDEN_SIZE, action_dim, 1,
              seed=SEED, buffer_size=MEMORY_BUFFER_SIZE,
              actor_lr=ACTOR_LR, actor_hidden_sizes=ACTOR_HIDDEN_UNITS, actor_weight_decay=ACTOR_WEIGHT_DECAY,
              critic_lr=CRITIC_LR, critic_hidden_sizes=CRITIC_HIDDEN_UNITS, critic_weight_decay=CRITIC_WEIGHT_DECAY,
              batch_size=BATCH_SIZE, gamma=GAMMA, tau=TAU
              )
print(agent)
agent.load()

scores, actor_losses, critic_losses = ddpg(n_episodes=N_EPISODES,
                                           eps_start=EPS_START, eps_decay=EPS_DECAY, eps_end=EPS_END,
                                           max_t=MAX_STEPS, learn_every_step=LEARN_EVERY_STEP)

agent.save()

fig = plt.figure()
ax1 = fig.add_subplot(311)
ax1.plot(np.arange(1, len(scores) + 1), scores)
ax1.set_ylabel('Score')
ax1.set_xlabel('Episode #')

ax2 = fig.add_subplot(312)
ax2.plot(np.arange(1, len(actor_losses) + 1), actor_losses)
# ax2.legend()
ax2.set_ylabel('Actor Loss')
ax2.set_xlabel('Episode #')

ax3 = fig.add_subplot(313)
ax3.plot(np.arange(1, len(critic_losses) + 1), critic_losses)
ax3.set_ylabel('Critic Loss')
ax3.set_xlabel('Episode #')
plt.savefig("training.png")

print('Done')
env.close()
