"""EduCore's versioned API for the Vue app (AGENT.md 4.4).

Called as /api/method/educore.api.v1.<module>.<function>. Every function checks permissions on the server;
the Vue app hiding a button is never the only guard. Responses come back in Frappe's {"message": …}
envelope; errors use Frappe's standard exception responses (exc_type, _server_messages).
"""
