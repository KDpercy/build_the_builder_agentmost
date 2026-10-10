# Patterns for phone-agent workflows (generic; each was learned from a failed test)

1. Counted rules live in routes, variables or fixed lines, not only in prompts.
   An instruction like "offer X once" or "attempt 1 uses X if the customer said Y" fails on
   repeat runs when it is only a prompt line. Extract the trigger as an enum, route to a
   node whose fixed spoken line makes the offer once, and compute the attempt plan in code.

2. A new route must yield to every rule that outranks it.
   Extract every higher-priority trigger the brief names (its "comes before" rules) into one
   enum, and require that enum to be empty on the new route. An unextracted value may be
   unset or an empty string: test both (is_not_set, or not_equals each value).

3. A word the brief forbids in one situation must not appear in fixed lines spoken in it.
   If the brief requires an idea that contains a restricted word, say the idea in other
   words. Scan every fixed line and every dictated sentence for each restricted word.

4. Every tool that can fail has a capped retry and an exit that still closes the call.
   Route on `<tool>_failure_count` greater_than a small number to a short node that
   apologises and closes. A failed closing call goes straight to the end node. Only an HTTP
   error counts as a failure; a reply with ok false is a normal result.

5. Rambling, cut-off or nonsense replies are never answers or refusals.
   Reply with a neutral line. Re-ask only questions that carry no offer. Never repeat an
   offer, an amount or a date because of such a reply. Always reply, even to one character.
   Sympathy words only for the triggers the brief names.

6. A one-time offer gets its own node with a fixed line. In that node check the decline
   first: a no anywhere in the node ends it; never ask again after a no.

7. List responses arrive flattened. A response_mapping of a list sets no variable; the
   engine writes `<node>_response.<path>.<index>.<field>`. Rebuild the list from those keys.

8. Stored tool arguments are named after the placeholder: a field whose default is
   `{{x_y}}` is stored as `<tool>_args.x_y`. A retry must reuse them under that name.

9. A retry of a recorded action is done by the workflow, not by the model: route on the
   failure count to a silent api_request node with the same arguments, then to a node that
   says what happened. Otherwise the model talks first and may ask the customer again.
