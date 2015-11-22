# behaviortreely.py
"""
behaviortreely.py is a friendly behavior tree implementation

it will run behavior trees defined in JSON format

1) prepare your tree JSON
2) instantiate a behaviortreely BT, load your tree JSON
3) register your task handlers, listeners to trigger on task events
4) run the tree: once, many times, ongoing, etc.
	- running via "start" activates the tree's tick time_started
	- you can tick the tree on your own instead to control its processing
"""

import json
import time
import threading
import random

"""
like the javascript setInterval, call a function repeatedly over time
"""
def callback_timer(callback, seconds):

	# wrap the callback to recursively keep calling it
	def callback_wrapper():
		callback_timer(callback, seconds)
		callback()

	# create a thread timer to be the pulse
	t = threading.Timer(seconds, callback_wrapper)

	# start the thread
	t.start()

	# return a reference to be able to stop the thread easily
	return t


"""
a place to store state for the behavior tree
"""
class Blackboard:

	_data = {}

	def store(node_path, data):
		_data[node_path] = data

	def fetch(node_path):
		if _data[node_path]:
			return _data[node_path]

"""
the root of a behavior, the behavior tree
"""
class BehaviorTree:

	tree_definition = None # json string of the tree document
	tree = None # tree parsed json object
	nodes = {} # instances of the node objects
	selectors = {} # registration dictionary of selector function references
	actions = {} # registration dictionary of action function references
	conditions = {} # registration dictionary of condition function references
	blackboard = None # the state of all nodes in the tree
	stopped = False # is the tree running
	current_composite_node = None # contains other nodes, controls flow order
	current_decorator_node = None # contains one node, controls flow lifecycle type
	current_leaf_node = None # a task or test/condition to run
	ticker = None # reference to the set timeout
	run_path_count = 0
	slug = ""

	def __init__(self, tree_definition_json):
		self.load(tree_definition_json)
		self.blackboard = Blackboard()

	"""
	load the json, the document that defines this tree
	"""
	def load(self, tree_definition_json):
		# loaded event
		self.tree_definition = tree_definition_json
		self.tree = json.loads(tree_definition_json)
		self.prepare_nodes(self.tree)

	"""
	start the heartbeat of the tree
	"""
	def start(self, seconds=1):
		# todo: fix the ticker, doesn't fully behave like a cancelable timer
		# started event
		self.ticker = callback_timer(self.tick, seconds)

	"""
	stop the heartbeat of the tree
	"""
	def stop(self):
		# stopped event
		if self.ticker is not None:
			self.ticker.cancel()

	"""
	run this node and its children
	"""
	def run_node(self, node):

		# run the node
		success = node["node"].run(self.blackboard, self)
		print("run_node success", success)

		# tree root node slug must be "root"
		# todo: enforce that/throw error
		if node["config"]["slug"] == "root":
			self.run_path_count += 1

		# track how many times this node is run
		node["node"].run_path_count = self.run_path_count
		node["node"].run_count += 1
		print(node["config"]["slug"], "tree: ", node["node"].run_path_count, "this node: ", node["node"].run_count)

		# now deal with the node's outcome

		# is this node a composite node?
		if isinstance(node["node"], Composite):
			print("this is a composite node")
			self.current_composite_node = node

		# is this node a decorator node?
		elif isinstance(node["node"], Decorator):
			print("this is a decorator node")
			self.current_decorator_node = node

		# is this node a leaf node?
		elif isinstance(node["node"], Leaf):
			print("this is a leaf node")
			self.current_leaf_node = node

		return success

	"""
	use the tree config to create instances of all the nodes
	"""
	def prepare_nodes(self, node):
		# get the nodes ready

		if not self.tree:
			print("error: tree missing")

		if node["slug"] == "root":
			# configure the root node
			self.nodes[self.tree["slug"]] = {}
			self.nodes[self.tree["slug"]]["config"] = self.tree

			# root node should be a decorator, determined in the root node's config
			module = __import__("behaviortreely")
			class_ = getattr(module, self.nodes[self.tree["slug"]]["config"]["type"])
			self.nodes[self.tree["slug"]]["node"] = class_(self.tree["slug"])
		else:
			self.nodes[node["slug"]] = {}
			self.nodes[node["slug"]]["config"] = node

			# composites
			if node["type"] == "Sequence":
				self.nodes[node["slug"]]["node"] = Sequence(node["slug"])
			elif node["type"] == "Parallel":
				self.nodes[node["slug"]]["node"] = Parallel(node["slug"])
			elif node["type"] == "ProbabilitySelector":
				self.nodes[node["slug"]]["node"] = ProbabilitySelector(node["slug"])
			elif node["type"] == "RandomSelector":
				self.nodes[node["slug"]]["node"] = RandomSelector(node["slug"])
			elif node["type"] == "RandomSequence":
				self.nodes[node["slug"]]["node"] = RandomSequence(node["slug"])
			elif node["type"] == "Selector":
				self.nodes[node["slug"]]["node"] = Selector(node["slug"])

			# decorators
			elif node["type"] == "RepeatAlways":
				self.nodes[node["slug"]]["node"] = RepeatAlways(node["slug"])
			elif node["type"] == "RepeatUntilFail":
				self.nodes[node["slug"]]["node"] = RepeatUntilFail(node["slug"])
			elif node["type"] == "RepeatUntilSuccess":
				self.nodes[node["slug"]]["node"] = RepeatUntilSuccess(node["slug"])
			elif node["type"] == "Inverter":
				self.nodes[node["slug"]]["node"] = Inverter(node["slug"])
			elif node["type"] == "LimitSemaphore":
				self.nodes[node["slug"]]["node"] = LimitSemaphore(node["slug"])
			elif node["type"] == "LimitTime":
				self.nodes[node["slug"]]["node"] = LimitTime(node["slug"])
			elif node["type"] == "LimitTries":
				self.nodes[node["slug"]]["node"] = LimitTries(node["slug"])

			# leaves
			elif node["type"] == "Action":
				self.nodes[node["slug"]]["node"] = Action(node["slug"])
			elif node["type"] == "Condition":
				self.nodes[node["slug"]]["node"] = Condition(node["slug"])


		# configure the child nodes
		for node_child in node["children"]:
			self.prepare_nodes(node_child)

	"""
	move the behavior tree forward
	"""
	def tick(self):
		# tick event

		print("running tick....")

		if self.stopped == False and self.tree:
			# todo: should the whole tree be run every tick?
			self.run_node(self.nodes[self.tree["slug"]])
		else:
			self.stop()

#----------------------
#----------------------

"""
all nodes besides the root are derived from BaseNode
"""
class BaseNode:

	run_path_count = 0
	run_count = 0
	slug = ""

	def __init__(self, _slug):
		print("creating ", type(self))
		self.slug = _slug

	# should override the run method
	def run(self, blackboard, tree):
		print("running ", type(self))
		return False


#----------------------
# Composite Nodes
#----------------------

"""
composite nodes can contain more than one child
"""
class Composite(BaseNode):

	def run(self, blackboard, tree):
		print("running ", type(self))
		# self.run_path_count += 1
		return True

"""
run child nodes in order
"""
class Sequence(Composite):

	def run(self, blackboard, tree):
		print("running ", type(self))
		return True

"""
run all child nodes at once
"""
class Parallel(Composite):

	def run(self, blackboard, tree):
		print("running ", type(self))

		# collect all the results
		results = [tree.run_node(childNode) for childNode in tree.nodes[self.slug]["config"]["children"]]

		if False in results:
			return False
		else:
			return True

"""
select one or more child nodes to run

depends up on selector handlers configured in the tree json and registered

as a reference with the behavior tree instance's selectors property
"""
class Selector(Composite):

	def run(self, blackboard, tree):
		print("running ", type(self))
		choices = [childNode["slug"] for childNode in tree.nodes[self.slug]["config"]["children"]]
		selector_handler_key = tree.nodes[self.slug]["config"]["selectorHandler"]
		chosen_slug = tree.selectors[selector_handler_key](choices, blackboard, tree)
		success = tree.run_node(tree.nodes[chosen_slug])
		return success

	def behavior():
		return

"""
randomly choose one child node
"""
class RandomSelector(Composite):

	def run(self, blackboard, tree):
		print("running ", type(self))
		success = True

		random_node = random.choice(tree.nodes[self.slug]["config"]["children"])
		print("random_node: ", random_node)
		chosen_slug = random_node["slug"]
		print("chosen_slug: ", chosen_slug)
		success = tree.run_node(tree.nodes[chosen_slug])

		return success

"""
select one child node based on a weighted chance
"""
def weighted_choice(choices):
	# add all the weights for the upper bound in the weighted search
	total = sum(w for c, w in choices)

	# get a position in the range between 0 and the upper bound
	r = random.uniform(0, total)

	# track position in the search toward upper bound
	upto = 0

	# search the weighted space to find the choice
	for c, w in choices:

		# choice is the one with its weight above the upper bound plus current position
		if upto + w >= r:
			return c

		# move up in the search
		upto += w

"""
take a chance
"""
class ProbabilitySelector(Composite):

	def run(self, blackboard, tree):
		print("running ", type(self))
		success = True
		choices = [(childNode["slug"], childNode["weight"]) for childNode in tree.nodes[self.slug]["config"]["children"]]
		chosen_slug = weighted_choice(choices)
		success = tree.run_node(tree.nodes[chosen_slug])
		return success

"""
take a chance on the order of things
"""
class RandomSequence(Composite):

	def run(self, blackboard, tree):
		print("running ", type(self))
		random.shuffle(tree.nodes[self.slug]["config"]["children"])

		for childNode in tree.nodes[self.slug]["config"]["children"]:
			success = tree.run_node(tree.nodes[childNode["slug"]])
			if success == False:
				break

		return success


#----------------------

"""
decorator - like a composite node with a single child
"""
class Decorator(BaseNode):

	def run(self, blackboard, tree):
		print("running ", type(self))
		return True


"""
never gonna stop
"""
class RepeatAlways(Decorator):

	def run(self, blackboard, tree):
		print("running ", type(self))
		print("repeating always")

		success = False

		# decorator should only have one child, run it
		success = tree.run_node(tree.nodes[tree.nodes[self.slug]["config"]["children"][0]["slug"]])

		if success == False:
			tree.stopped = True

		return success


"""
try until not gonna
"""
class RepeatUntilFail(Decorator):

	def run(self, blackboard, tree):
		print("running ", type(self))
		print("repeating until fail")

		success = False

		# decorator should only have one child, run it
		success = tree.run_node(tree.nodes[tree.nodes[self.slug]["config"]["children"][0]["slug"]])

		if success == False:
			tree.stopped = True

		return success

"""
succeed and move on
"""
class RepeatUntilSuccess(Decorator):

	def run(self, blackboard, tree):
		print("running ", type(self))
		print("repeating until success")

		success = False

		# decorator should only have one child, run it
		success = tree.run_node(tree.nodes[tree.nodes[self.slug]["config"]["children"][0]["slug"]])

		if success is True:
			tree.stopped = True

		return success

"""
succeeds if task fails
"""
class Inverter(Decorator):

	def run(self, blackboard, tree):
		print("running ", type(self))
		print("inverter succeeds if task fails")

		success = False

		# decorator should only have one child, run it
		success = tree.run_node(tree.nodes[tree.nodes[self.slug]["config"]["children"][0]["slug"]])

		if success is True:
			return False
		else:
			return True

"""
limit total tries
"""
class LimitTries(Decorator):

	tries_limit = None
	tries = 0

	def run(self, blackboard, tree):
		print("running ", type(self))

		if not self.tries_limit:
			self.tries_limit = tree.nodes[self.slug]["config"]["limit"]


		if self.tries >= self.tries_limit:
			tree.stopped = True
			return False
		else:
			self.tries += 1
			# decorator should only have one child, run it
			return tree.run_node(tree.nodes[tree.nodes[self.slug]["config"]["children"][0]["slug"]])

"""
limit by time
"""
class LimitTime(Decorator):

	time_started = None
	time_limit = None

	def run(self, blackboard, tree):
		print("running ", type(self))

		if not self.time_limit:
			self.time_limit = tree.nodes[self.slug]["config"]["limit"]

		if not self.time_started:
			self.time_started = time.time()

		current = time.time()

		print("time passed: ", str(current - self.time_started))

		if current - self.time_started >= self.time_limit:
			tree.stopped = True
			return False
		else:
			# decorator should only have one child, run it
			return tree.run_node(tree.nodes[tree.nodes[self.slug]["config"]["children"][0]["slug"]])


# todo:
# """
# limits how many behavior tree actors can use
# a given resource
# """
# class LimitSemaphore(Decorator):

# 	def run(self, blackboard, tree):
# 		print("running ", type(self))
# 		return True


#----------------------

"""
leaf - where tasks are run: actions or conditions
"""
class Leaf(BaseNode):

	def run(self, blackboard, tree):
		print("running ", type(self))
		return True


"""
use actions to make stuff happen

depends up on action handlers configured in the tree json and registered

as a reference with the behavior tree instance's actions property
"""
class Action(Leaf):

	def run(self, blackboard, tree):
		print("running ", type(self))

		action_key = tree.nodes[self.slug]["config"]["actionHandler"]

		return tree.actions[action_key]()


"""
use conditions to determine if this node or tree of nodes should keep running

depends up on condition handlers configured in the tree json and registered

as a reference with the behavior tree instance's conditions property
"""
class Condition(Leaf):

	def run(self, blackboard, tree):
		print("running ", type(self))

		condition_key = tree.nodes[self.slug]["config"]["conditionHandler"]

		return tree.conditions[condition_key]()


#----------------------
# running as a script instead of an imported module:
#----------------------

if __name__ == '__main__':

	test_json = """
{
	"nodeName":"root of behavior XYZ",
	"goal":"to test behaviortreely",
	"description":"this is the root",
	"slug":"root",
	"type":"LimitTime",
	"limit":7,
	"weight":0,
	"time_started":null,
	"tries":null,
	"selectorHandler":null,
	"conditionHandler":null,
	"actionHandler":null,
	"children":[
		{
			"nodeName":"try to win",
			"slug":"try-your-best0",
			"description":"keep trying your best",
			"type":"Selector",
			"weight":0.5,
			"parameters":[],
			"children":[
				{
					"nodeName":"try to win1",
					"slug":"try-your-best1",
					"description":"keep trying your best1",
					"type":"Action",
					"weight":0.6,
					"parameters":[],
					"children":[],
					"successHandler":null,
					"failHandler":null,
					"selectorHandler":null,
					"conditionHandler":null,
					"actionHandler":"do a test action",
					"parentNodeSlug":"root"

				},
				{
					"nodeName":"try to win2",
					"slug":"try-your-best2",
					"description":"keep trying your best2",
					"type":"Action",
					"weight":0.5,
					"parameters":[],
					"children":[],
					"successHandler":null,
					"failHandler":null,
					"selectorHandler":null,
					"conditionHandler":null,
					"actionHandler":"do a test action",
					"parentNodeSlug":"root"

				},
				{
					"nodeName":"try to win3",
					"slug":"try-your-best3",
					"description":"keep trying your best3",
					"type":"Action",
					"weight":0.9,
					"parameters":[],
					"children":[],
					"successHandler":null,
					"failHandler":null,
					"selectorHandler":null,
					"conditionHandler":null,
					"actionHandler":"do a test action",
					"parentNodeSlug":"root"

				}
			],
			"successHandler":null,
			"failHandler":null,
			"selectorHandler":"do a test selector",
			"conditionHandler":null,
			"actionHandler":null,
			"parentNodeSlug":"root"

		}
	]
}
	"""

	def condition_test():
		print("running a condition")
		return True

	def action_test():
		print("running an action")
		return True

	def selector_test(choices, blackboard, tree):
		# could do a lot more than this to provide proper slug from choices
		return choices[0]

	print("starting as script...")

	# create the behavior tree instance
	bt = BehaviorTree(test_json)

	# register any needed actions, conditions, or selectors referred to in the JSON
	bt.actions["do a test action"] = action_test
	bt.conditions["do a test condition"] = condition_test
	bt.selectors["do a test selector"] = selector_test

	# use start() instead of tick() to keep the behavior tree running
	# bt.start()

	# use tick() to run the tree once
	bt.tick()
