// AIT performances are organised using the join_key
// All agent that use this join_key are part of the same conversation
// This script resets the conversation that belongs to the join_key


integer command_channel = 8; // Change this to any channel of your choice.
integer listener;

string join_key;

string simulatorHostname;
string regionName;

string joinkeyNotecardName = "join_key";
key joinkeyNotecardQueryId;


list whitelisted_users = [];
string whitelistNotecardName = "whitelist";
key whitelistNotecardQueryId;
integer whitelistCurrentLine=0;


integer max_response_length = 16384;

reset_theater_play(string join_key) {
    llHTTPRequest("http://hg.hypergrid.net:7999/ait/stopJoinkey", [HTTP_METHOD, "POST", HTTP_BODY_MAXLENGTH, max_response_length, HTTP_MIMETYPE, "application/json"], "{
        \"join_key\": \""+join_key+"\"
    }");
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

                string line = [data];

                join_key = line;
                llOwnerSay("join_key has been read " + join_key);
                llOwnerSay("On channel " + command_channel + " you can reset the theater performance/conversation with join_key "+ join_key + " with the following command: resetAIT " +join_key);

                llListen(command_channel, "","","");
            }
        }
        if (query_id == whitelistNotecardQueryId)
        {
            if (data != EOF)
            {

                string line = [data];
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
        string username = llParseString2List(name, ["@"], [])[0];
        username = llStringTrim(username, 3);
        if (llListFindList(whitelisted_users, [username]) == -1){
            //llInstantMessage(avatarKey,"User is not in list of valid users");
            return;
        }

        if (channel == command_channel) {
            // Handle both dialog responses and channel commands
            if (message == "ResetAIT") {
                llInstantMessage(id, "Conversation " + join_key + " has been reset");
                reset_theater_play(join_key);
            }
            else if (message == "Status") {
                llInstantMessage(id, "AIT Controller Status:");
                llInstantMessage(id, "Join Key: " + join_key);
                llInstantMessage(id, "Channel: " + (string)command_channel);
                llInstantMessage(id, "Whitelisted users: " + (string)llGetListLength(whitelisted_users));
            }
            else if (message == "Close") {
                llInstantMessage(id, "Dialog closed.");
            }
            else {
                // Handle channel commands
                string respondingTo = "resetAIT " + join_key;
                if(message==respondingTo) {
                    llInstantMessage(id, "Conversation " + join_key + " has been reset");
                    reset_theater_play(join_key);
                }
            }
        }
    }

    touch_start(integer total_number)
    {
        key toucher = llDetectedKey(0);
        string username = llParseString2List(llKey2Name(toucher), ["@"], [])[0];
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

// Function to show dialog interface
showDialog(key user)
{
    llDialog(user, 
        "AIT Controller for Join Key: " + join_key + "\nChannel: " + (string)command_channel + "\n\nWhat would you like to do?",
        ["ResetAIT", "ActivateAllCharacters", "DeactivateAllCharacters", "Status", "Close"], 
        command_channel);
}