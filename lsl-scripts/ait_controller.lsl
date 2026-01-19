// AI Talkmaster conversations are organised using the join_key.
// All agents that use this join_key are part of the same conversation.
// This script resets the conversation that belongs to the join_key.
// This is simply a reset of the conversation history.
// More details at https://github.com/geschnee/ai-talkmaster

// This script provides the following options (on-click):
// StartConversation - This starts the audio server for the join_key (if it hasn't been started) and gives you information about the audio link.
// ResetAIT - This resets the join_key's history (the characters forget what was said).
// ActivateAllCharacters - All characters in local chat recieve the activation command, this is a helper function. You can also activate them directly (by clicking on a character / chat).
// DeactivateAllCharacters - All characters in local chat recieve the deactivation command, this is a helper function. You can also deactivate them directly (by clicking on a character / chat).
// Status - Prints this script's loaded properties (command channel, users that can use this script (whitelisted) and join_key).


integer command_channel = 8; // Change this to any channel of your choice.
integer listener;

string join_key;

string ait_endpoint = "https://hg.hypergrid.net:6000";

string joinkeyNotecardName = "join_key";
key joinkeyNotecardQueryId;


list whitelisted_users = [];
string whitelistNotecardName = "controller-whitelist";
key whitelistNotecardQueryId;
integer whitelistCurrentLine=0;


integer max_response_length = 16384;

// Variables to track the single reset request
key reset_request_id = NULL_KEY;
key reset_user_key = NULL_KEY;

// Variables to track the single start conversation request
key start_conversation_request_id = NULL_KEY;
key start_conversation_user_key = NULL_KEY;

reset_aitalkmaster(string join_key, key user_key) {
    string jsonBody = llList2Json(JSON_OBJECT, ["join_key", join_key]);

    reset_request_id = llHTTPRequest(ait_endpoint + "/ait/resetJoinkey", [HTTP_METHOD, "POST", HTTP_BODY_MAXLENGTH, max_response_length, HTTP_MIMETYPE, "application/json"], jsonBody);
    
    // Store the user key for this request
    reset_user_key = user_key;
}

start_conversation(string join_key, key user_key) {
    string jsonBody = llList2Json(JSON_OBJECT, ["join_key", join_key]);

    start_conversation_request_id = llHTTPRequest(ait_endpoint + "/ait/startConversation", [HTTP_METHOD, "POST", HTTP_BODY_MAXLENGTH, max_response_length, HTTP_MIMETYPE, "application/json"], jsonBody);
    
    // Store the user key for this request
    start_conversation_user_key = user_key;
}

// Function to show dialog interface
showDialog(key user)
{
    llDialog(user, 
        "AIT Controller for Join Key: " + join_key + "\nChannel: " + (string)command_channel + "\n\nWhat would you like to do?",
        ["ResetAIT " + join_key, "StartConversation "+ join_key, "ActivateAllCharacters", "DeactivateAllCharacters", "Status", "Close"], 
        command_channel);
}

default
{
    state_entry()
    {
        // Verify the notecard exists
        if (llGetInventoryType(joinkeyNotecardName) != INVENTORY_NOTECARD)
        {
            llOwnerSay("Error: Notecard '" + joinkeyNotecardName + "' not found.");
            return;
        }
        if (llGetInventoryType(whitelistNotecardName) != INVENTORY_NOTECARD)
        {
            llOwnerSay("Error: Notecard '" + whitelistNotecardName + "' not found.");
            return;
        }
        
        joinkeyNotecardQueryId = llGetNotecardLine(joinkeyNotecardName, 0);

        key ownerKey = llGetOwner();         
        string ownerName = llKey2Name(ownerKey);
        whitelisted_users += [ownerName];
        whitelistNotecardQueryId = llGetNotecardLine(whitelistNotecardName, whitelistCurrentLine);
    }

    dataserver(key query_id, string data)
    {
        if (query_id == joinkeyNotecardQueryId)
        {
            if (data != EOF)
            {

                string line = data;

                join_key = line;
                llOwnerSay("join_key has been read " + join_key);
                llOwnerSay("On channel " + (string) command_channel + " you can reset the theater performance/conversation with join_key "+ join_key + " with the following command: ResetAIT " +join_key);

                llListen(command_channel, "","","");
            }
        }
        if (query_id == whitelistNotecardQueryId)
        {
            if (data != EOF)
            {

                string line = data;
                whitelisted_users += [line];
                
                // Get the next line
                whitelistCurrentLine++;
                whitelistNotecardQueryId = llGetNotecardLine(whitelistNotecardName, whitelistCurrentLine);
            }
            else
            {
                
                // Now you have the entire notecard as a single string
                llOwnerSay("Whitelist loaded:");
                integer i = 0;
                for (i = 0; i < llGetListLength(whitelisted_users); ++i)
                {
                    // Convert each element to string for printing
                    llOwnerSay(llList2String(whitelisted_users, i));
                }

            }
        }
    }

    listen(integer channel, string name, key id, string message)
    {
        string username = llList2String(llParseString2List(name, ["@"], []), 0);
        username = llStringTrim(username, 3);
        if (llListFindList(whitelisted_users, [username]) == -1){
            //llInstantMessage(avatarKey,"User is not in list of valid users");
            return;
        }

        if (channel == command_channel) {
            // Handle both dialog responses and channel commands
            if (message == "ResetAIT "+join_key) {
                llInstantMessage(id, "Resetting conversation " + join_key + "...");
                reset_aitalkmaster(join_key, id);
            }
            else if (message == "StartConversation "+ join_key) {
                llInstantMessage(id, "Starting conversation " + join_key + "...");
                start_conversation(join_key, id);
            }
            else if (message == "Status") {
                llInstantMessage(id, "AIT Controller Status:");
                llInstantMessage(id, "Join Key: " + join_key);
                llInstantMessage(id, "Channel: " + (string)command_channel);
                llInstantMessage(id, "Whitelisted users (" + (string)llGetListLength(whitelisted_users) + "):");
                integer i = 0;
                for (i = 0; i < llGetListLength(whitelisted_users); ++i)
                {
                    llInstantMessage(id, "  - " + llList2String(whitelisted_users, i));
                }
            }
            else if (message == "Close") {
                llInstantMessage(id, "Dialog closed.");
            }
        }
    }

    http_response(key request_id, integer status, list metadata, string body)
    {
        // Check if this is the reset request
        if (request_id == reset_request_id) {
            // Found the request - get the associated user key
            key user_key = reset_user_key;
            
            // Clear the tracking variables
            reset_request_id = NULL_KEY;
            reset_user_key = NULL_KEY;
            
            // Notify the user based on the response status
            if (status == 200) {
                llInstantMessage(user_key, "Success: Conversation " + join_key + " has been reset successfully.");
                llSay(0, "Conversation " + join_key + " has been reset successfully.");
                
                string stream_url = llJsonGetValue(body, ["stream_url"]);

                if (stream_url != "") {
                    llSay(0, "Audio Stream is available at: " + stream_url);
                    llInstantMessage(user_key, "Audio Stream is available at: " + stream_url);
                }
            } else {
                llInstantMessage(user_key, "Error: Failed to reset conversation " + join_key + ". Status: " + (string)status + " - " + body);
                llOwnerSay("Error:" + (string) status + " - " + body);
            }
            return;
        }
        
        // Check if this is the start conversation request
        if (request_id == start_conversation_request_id) {
            // Found the request - get the associated user key
            key user_key = start_conversation_user_key;
            
            // Clear the tracking variables
            start_conversation_request_id = NULL_KEY;
            start_conversation_user_key = NULL_KEY;
            
            // Notify the user based on the response status
            if (status == 200) {
                string info = llJsonGetValue(body, ["info"]);
                string stream_url = llJsonGetValue(body, ["stream_url"]);
                
                if (info != "") {
                    llInstantMessage(user_key, "Success: " + info);
                } else {
                    llInstantMessage(user_key, "Success: Conversation " + join_key + " has been started successfully.");
                }
                
                if (stream_url != "") {
                    llInstantMessage(user_key, "Audio Stream is available at: " + stream_url);
                }
            } else if (499 == status) {
                // ignore 499 client timeouts, they occur frequently on OpenSimulator Community Conference grid
                return;
            } else {
                llInstantMessage(user_key, "Error: Failed to start conversation " + join_key + ". Status: " + (string)status + " - " + body);
            }
            return;
        }
    }

    touch_start(integer total_number)
    {
        key toucher = llDetectedKey(0);
        string username = llList2String(llParseString2List(llKey2Name(toucher), ["@"], []), 0);
        username = llStringTrim(username, 3);
        
        if (llListFindList(whitelisted_users, [username]) != -1) {
            showDialog(toucher);
        } else {
            llInstantMessage(toucher, "You are not authorized to use this controller.");
        }
    }
    
    // If changes are done to object inventory then reset the script.
    changed(integer a)
    {
        if(a & CHANGED_INVENTORY ) {
            llResetScript();
        }
    }
}