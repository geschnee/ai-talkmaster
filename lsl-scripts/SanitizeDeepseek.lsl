// this script only contains a single function that can be used to sanitize a response from the AI Talkmaster server.
// The Ollama deeoseek-r1 model returns a response starting with a <think>...</think> block. This function removes the <think>...</think> block from the response.

string removeThinkBlock(string message)
{

    string substring = "</think>";
    integer position = llSubStringIndex(message, substring);

    if (position == -1) // Substring not found
        return message;

    return llDeleteSubString(message, 0, position + llStringLength(substring) - 1);
}
