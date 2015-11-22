# behavortreely.py

A behavior tree implementation in Python. It runs behavior trees defined in JSON format and will trigger actions in your code.

**Note:** this is the first full working draft of behavortreely.py, the example, especially the JSON is very place holder. I intend to update this in the coming days and weeks to be better documented. Probably just cursed myself by by saying that. Ah well.

## Overview

1) Prepare your tree JSON.
2) Instantiate a behavortreely BehaviorTree by loading your tree JSON.
3) Register your action handlers, condition handlers, and selector handlers if needed.
4) Run the tree: once, many times, ongoing, etc.
    - Run via start() activates the tree's ongoing tick
    - Or run via tick() run it once

## Example

    test_json = """
    {
        "nodeName":"root of behavior XYZ",
        "goal":"to test treely",
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