// script by Herzstein Dev
// This script provides a way of interacting with the AI Talkmaster Conversation functionality.
// When the user clicks the object, it starts a conversation. The user's messages get sent to the server and the replies are sent to the in-world chat.
// This conversation has history. The user and object can talk back-and-forth.
// More details at https://github.com/geschnee/ai-talkmaster

string ait_endpoint = "https://hg.hypergrid.net:6000";

integer com_channel = 0;
integer listener;
string message;
key user=NULL_KEY;
string username ="";
float reserveTime = 180.0;
float pollFreq = 2.0;
float stopwatch;

integer command_channel = 8;


string conversation_key;
float conversation_time=0;
key conversation_message_id=NULL_KEY;
integer pollingResponse=0;

integer max_response_length = 16384;

// Polling timeout variables
float polling_start_time = 0.0;
float polling_timeout = 300.0; // Stop polling after 5 minutes

float CONVERSATION_INCREMENT=60;

integer MAX_LENGTH = 1024;    // Maximum string length in LSL

string regionName;

// Validation variables
key modelsValidationId;
integer modelsValidated = 0;
integer validationInProgress = 0;

// HTTP request tracking
key startConversationId;
key postMessageId;
key getMessageResponseId;

// Notecard completion tracking
integer notecardsCompleted = 0;
integer PARAMETERS_NOTECARD_COMPLETED = 1;
integer SYSTEM_NOTECARD_COMPLETED = 2;
integer ALL_NOTECARDS_COMPLETED = 3; // 1 + 2 = 3

// Read Entire Notecard as Single String
string parametersNotecardName = "llm-parameters";
string systemNotecardName = "llm-system"; 
key parametersNotecardQueryId;
key systemNotecardQueryId;
integer parametersCurrentLine = 0;
integer systemCurrentLine = 0;
list systemNotecardLines = [];


string charactername;
string model;
string system;

list optionParameters_stringlist = ["stop"];
list optionParameters_integers = ["num_ctx","repeat_last_n", "seed", "num_predict", "top_k"];
list optionParameters_floats = ["repeat_penalty","temperature","top_p","min_p"];

// List to store option key-value pairs
list optionsList = [];


// Function to print response text, splitting into chunks if necessary
printResponse(string response) {
    integer textLength = llStringLength(response);
    list chunks = [];
    
    // If text is already short enough, print it directly
    if (textLength <= MAX_LENGTH)
    {
        llSay(0, response);
        return;
    }
    
    integer currentPos = 0;
    
    while (currentPos < textLength)
    {
        integer endPos = currentPos + MAX_LENGTH;
        
        // Make sure we don't go beyond the text length
        if (endPos > textLength)
        {
            endPos = textLength;
        }
        
        // If we're not at the end of the text, try to find a natural breaking point
        if (endPos < textLength)
        {
            // First try to break at a newline
            integer newlinePos = -1;
            integer i;
            
            // Find the rightmost newline in our range
            for (i = endPos - 1; i >= currentPos; --i)
            {
                if (newlinePos==-1 && llGetSubString(response, i, i) == "\n")
                {
                    newlinePos = i;
                }
            }
            
            if (newlinePos != -1)
            {
                // Found a newline, break there (include the newline in the chunk)
                endPos = newlinePos + 1;
            }
            else
            {
                // No newline found, try to break at a space
                integer spacePos = -1;
                
                // Find the rightmost space in our range
                for (i = endPos - 1; i >= currentPos; --i)
                {
                    if (spacePos == -1 && llGetSubString(response, i, i) == " ")
                    {
                        spacePos = i;
                    }
                }
                
                if (spacePos != -1)
                {
                    // Found a space, break there (include the space in the chunk)
                    endPos = spacePos + 1;
                }
            }
        }
        
        // Add the chunk to our list
        chunks += [llGetSubString(response, currentPos, endPos - 1)];
        currentPos = endPos;
    }
    
    // Print all chunks with numbering
    integer j;
    for (j = 0; j < llGetListLength(chunks); ++j)
    {
        string chunk = llList2String(chunks, j);
        integer j_plus = j + 1;
        llSay(0, (string) j_plus + " " + chunk);
    }
}

add_stringlist_option(string optionname, string value) {
    optionsList += [optionname, llList2Json(JSON_ARRAY, [value])];
}

add_int_option(string optionname, integer num) {
    optionsList += [optionname, num];
}

add_float_option(string optionname, float num) {
    optionsList += [optionname, num];
}

// Add option with automatic type detection
add_option(string optionname, string value) {
    // Check which type list contains this parameter
    if (llListFindList(optionParameters_stringlist, [optionname]) != -1) {
        add_stringlist_option(optionname, value);
    } else if (llListFindList(optionParameters_integers, [optionname]) != -1) {
        integer intValue = (integer)value;
        add_int_option(optionname, intValue);
    } else if (llListFindList(optionParameters_floats, [optionname]) != -1) {
        float floatValue = (float)value;
        add_float_option(optionname, floatValue);
    } else {
        llOwnerSay("Unknown option: " + optionname);
    }
}

validateModel(string modelToValidate)
{
    if (validationInProgress) {
        llOwnerSay("Validation already in progress, please wait...");
        return;
    }
    
    validationInProgress = 1;
    llOwnerSay("Validating model: " + modelToValidate);
    modelsValidationId = llHTTPRequest(ait_endpoint + "/chat_models", 
        [HTTP_METHOD, "GET", HTTP_MIMETYPE, "application/json"], "");
}

// Function to check if a value exists in a JSON array
integer isValueInJsonArray(string jsonString, string value)
{
    // Simple check for the value in the JSON string
    // This is a basic implementation - in a real scenario you'd want more robust JSON parsing
    if (llSubStringIndex(jsonString, "\"" + value + "\"") != -1) {
        return TRUE;
    }
    return FALSE;
}

// Function to validate all parameters after they are loaded
validateAllParameters()
{
    llOwnerSay("Starting parameter validation...");
    validateModel(model);
}

start_conversation(string username) {
    // Check if model validation has completed and failed
    if (validationInProgress == 0 && modelsValidated == 0) {
        llSay(0, "Model '" + model + "' is not available on the server. Please check your configuration.");
        return;
    }
    
    // If validation is still in progress, wait
    if (validationInProgress == 1) {
        llSay(0, "Model validation is still in progress. Please wait...");
        return;
    }

    string optionstring = llList2Json(JSON_OBJECT, optionsList);
    string jsonBody = llList2Json(JSON_OBJECT, ["username", username, "model", model,"system_instructions", system, "options", optionstring]);
    
    string instructions = llReplaceSubString(system, "\"", "\\\"", 0);
    startConversationId = llHTTPRequest(ait_endpoint + "/conversation/start", [HTTP_METHOD, "POST", HTTP_BODY_MAXLENGTH, max_response_length, HTTP_MIMETYPE, "application/json"], jsonBody);
}

conversation_postMessage(string conversation_key, string message) {
    // Check if model validation has completed and failed
    if (validationInProgress == 0 && modelsValidated == 0) {
        llSay(0, "Model '" + model + "' is not available on the server. Please check your configuration.");
        return;
    }
    
    // If validation is still in progress, wait
    if (validationInProgress == 1) {
        llSay(0, "Model validation is still in progress. Please wait...");
        return;
    }

    conversation_message_id = llGenerateKey();

    string jsonBody = llList2Json(JSON_OBJECT, ["conversation_key", conversation_key, "message", message, "message_id", (string) conversation_message_id]);
    
    postMessageId = llHTTPRequest(ait_endpoint + "/conversation/postMessage", [HTTP_METHOD, "POST", HTTP_BODY_MAXLENGTH, max_response_length, HTTP_MIMETYPE, "application/json"], jsonBody);
}

conversation_getMessageResponse(string conversation_key) {
    string uriParams = "?conversation_key=" + conversation_key + "&message_id=" + (string) conversation_message_id;

    getMessageResponseId = llHTTPRequest(ait_endpoint + "/conversation/getMessageResponse" + uriParams, [HTTP_METHOD, "GET", HTTP_BODY_MAXLENGTH, max_response_length, HTTP_MIMETYPE, "application/json"], "");
}

set_ready() {
    llListenRemove(listener);
    llListenRemove(command_channel);
    llSetTimerEvent(0);
    user=NULL_KEY;
    username="";
    message="";

    
    llSetText("Please click on me to start a new session.", <1.0, 1.0, 0.5>, 1.0);

    llSay(0, "Please click on me to start a new session.");
    llSay(0, "---");
}

default
{
    state_entry()
    {
        // Verify the notecard exists
        if (llGetInventoryType(parametersNotecardName) != INVENTORY_NOTECARD)
        {
            llOwnerSay("Error: Notecard '" + parametersNotecardName + "' not found. Please add it to the object.");
            return;
        }
        if (llGetInventoryType(systemNotecardName) != INVENTORY_NOTECARD)
        {
            llOwnerSay("Error: Notecard '" + systemNotecardName + "' not found. Please add it to the object.");
            return;
        }
        // Start reading the notecard from the first line

        optionsList = [];
        parametersNotecardQueryId = llGetNotecardLine(parametersNotecardName, parametersCurrentLine);
        systemNotecardQueryId = llGetNotecardLine(systemNotecardName, systemCurrentLine);

        set_ready();
    }

    dataserver(key query_id, string data)
    {
        if (query_id == parametersNotecardQueryId)
        {
            if (data != EOF)
            {

                string line = data;

                list splits = llParseString2List(line, [":"],[]);
                
                if ( llGetListLength(splits) == 2 ) 
                {
                    string paramName = llList2String(splits, 0);
                    string value = llList2String(splits, 1);

                    if (paramName == "charactername") 
                    {
                        charactername = value;
                    }
                    if (paramName == "model") 
                    {
                        model = value;
                    }
                    
                    // Check if this parameter is in any of our option lists
                    integer isStringListParam = (llListFindList(optionParameters_stringlist, [paramName]) != -1);
                    integer isIntParam = (llListFindList(optionParameters_integers, [paramName]) != -1);
                    integer isFloatParam = (llListFindList(optionParameters_floats, [paramName]) != -1);
                    
                    if (isStringListParam || isIntParam || isFloatParam) {
                        add_option(paramName, value);
                    }
                }
                // Get the next line
                parametersCurrentLine++;
                parametersNotecardQueryId = llGetNotecardLine(parametersNotecardName, parametersCurrentLine);
            }
            else
            {
                
                // Now you have the entire notecard as a single string
                llOwnerSay("Parameter notecard content loaded:");
                llOwnerSay("charactername: " + charactername);
                llOwnerSay("model: " + model);
                
                notecardsCompleted = notecardsCompleted | PARAMETERS_NOTECARD_COMPLETED;
                
                // Check if all notecards are completed
                if (notecardsCompleted == ALL_NOTECARDS_COMPLETED) {
                    validateAllParameters();
                }
            }
        }
        if (query_id == systemNotecardQueryId)
        {
            if (data != EOF)
            {

                string line = data;

                // Add this line to our collection
                systemNotecardLines += line;
                
                // Get the next line
                systemCurrentLine++;
                systemNotecardQueryId = llGetNotecardLine(systemNotecardName, systemCurrentLine);
            }
            else
            {
                // We've reached the end of the notecard
                // Combine all lines into a single string with newlines
                string entireContent = llDumpList2String(systemNotecardLines, "\n");
                
                if (entireContent == "") {
                    llOwnerSay(systemNotecardName + " should not be empty for use as llm system instructions");
                    return;
                }
                
                // Now you have the entire notecard as a single string
                llOwnerSay("System instructions loaded from notecard:");
                llOwnerSay(entireContent);

                system = entireContent;
                
                notecardsCompleted = notecardsCompleted | SYSTEM_NOTECARD_COMPLETED;
                
                // Check if all notecards are completed
                if (notecardsCompleted == ALL_NOTECARDS_COMPLETED) {
                    validateAllParameters();
                }
            }
        }
    }

    touch_start(integer num_detected)
    {
        if (notecardsCompleted != ALL_NOTECARDS_COMPLETED) {
            llSay(0, "Error: Configuration notecards not loaded properly. Please check that 'llm-parameters' and 'llm-system' notecards exist and contain valid data. Reset the script for more details.");
            return;
        }
        if (validationInProgress == 1) {
            llSay(0, "Model validation is still in progress. Please wait...");
            return;
        }
        if (validationInProgress == 0 && modelsValidated == 0) {
            llSay(0, "Error: Model validation failed. Model '" + model + "' is not available on the server. Please check your configuration.");
            return;
        }
        if (user!=NULL_KEY & llDetectedKey(0) != user) {
            llSay(0, "Sorry I am currently in use by " + llKey2Name(user) + ". Please await your turn." );
        } else if (user!=NULL_KEY && llDetectedKey(0) == user ) {
            if (pollingResponse == 1) {
                llInstantMessage(user, "Conversation in progress, I am waiting for the generated response. You can abort this conversation on channel" + (string) command_channel + " with this command: ExitConversation");
            } else {
                llInstantMessage(user, "You can send more messages.");
            }            
        } else {
            user = llDetectedKey(0);
            
            llSay(0, "Hello "+llKey2Name(user)+" I am made to forward your input to " + charactername + ". I can deal only with one user at a time We can have a conversation with many messages."); 
            username = llKey2Name(user);
            
            llSetText("Waiting for message by " + llKey2Name(user), <1.0, 1.0, 0.5>, 1.0);
            stopwatch = 0;
            message="";
            conversation_key="";
            llSetTimerEvent(pollFreq);

            start_conversation(username);
        }
    }

    listen(integer channel, string name, key id, string message)
    {
        if(conversation_key==""){
            return;
        }
        if(channel == command_channel && message == "ExitConversation" && id == user) {
            llSay(0, "Thank you for being here today "+username+". The session is finished, click to start a fresh one");
            set_ready();
        }
        if(channel == com_channel && id == user) {
            stopwatch=0;
            
            conversation_postMessage(conversation_key, message);
            pollingResponse=1;
            polling_start_time = llGetUnixTime(); // Record when polling started
            // Show polling indicator
            llSetText("waiting for response", <1.0, 1.0, 0.5>, 1.0);
            llListenRemove(listener);
            llListenRemove(command_channel);
        }   
    }

    http_response(key request_id, integer status, list metadata, string body)
    {
        // Handle validation responses
        if (request_id == modelsValidationId) {
            if (status == 200) {
                llOwnerSay("Models validation response received");
                string chatModels = llJsonGetValue(body, ["chat_models"]);
                string defaultModel = llJsonGetValue(body, ["default_model"]);

                if (model==""){
                    llOwnerSay("model was not specified in llm-parameters notecard, the AIT default model " + defaultModel + " will be used");
                    modelsValidated = 1;
                } else {
                    if (isValueInJsonArray(chatModels, model)) {
                        llOwnerSay("✓ Model '" + model + "' is valid");
                        modelsValidated = 1;
                        llSetText("Please click on me to start a new session.", <1.0, 1.0, 0.5>, 1.0);
                    } else {
                        llOwnerSay("✗ Model '" + model + "' is NOT valid. Available models: " + chatModels);
                        modelsValidated = 0;
                    }
                }
                
                validationInProgress = 0;
            } else {
                llOwnerSay("Error validating model: HTTP " + (string)status + " - " + body);
                validationInProgress = 0;
            }
            return;
        }
        
        // Handle start conversation response
        if (request_id == startConversationId) {
            if (status == 200) {
                if (username == ""){
                    //llSay(0, "reset was called between request and response");
                    return;
                }
                string local_conversation_key = llJsonGetValue(body, ["conversation_key"]);
               
                conversation_key = local_conversation_key;
                llSay(0, "Please enter something you want to say to " + charactername + " in chat.");
                // new conversation was started on backend
                conversation_time=0;
                pollingResponse=0;

                listener = llListen(com_channel, "", user, "");
                llListen(command_channel, "", user, "");
            } else {
                llOwnerSay("Error starting conversation: HTTP " + (string)status + " - " + body);
                llSay(0, "Sorry, there was an error starting the conversation. Please try again.");
                set_ready();
            }
            return;
        }
        
        // Handle postMessage and getMessageResponse responses
        if (request_id == postMessageId || request_id == getMessageResponseId) {
            if(200 == status) {
                if (username == ""){
                    //llSay(0, "reset was called between request and response");
                    return;
                }
                
                string message_id = llJsonGetValue(body, ["message_id"]);
                if (message_id!=(string) conversation_message_id){
                    return;
                }

                // start listening to user messages again
                pollingResponse=0;
                conversation_message_id=NULL_KEY;
                listener = llListen(com_channel, "", user, "");
                llListen(command_channel, "", user, "");
                conversation_time = conversation_time + CONVERSATION_INCREMENT;

                

                string response = llJsonGetValue(body, ["response"]);

                llSay(0, username+" that's for you: ");

                printResponse(response);

                
                llSetText("Continue chatting on channel 0", <1.0, 1.0, 0.5>, 1.0);
                
                return;
            } else if (status != 0 && status != 425 && status != 499) {
                // Stop polling on any error status (not 0, not 200, not 425, not 499)
                if (pollingResponse == 1) {
                    pollingResponse = 0;
                    conversation_message_id = NULL_KEY;
                    listener = llListen(com_channel, "", user, "");
                    llListen(command_channel, "", user, "");
                    // Clear polling indicator
                    llSetText("Please click on me to start a new session.", <1.0, 1.0, 0.5>, 1.0);
                    llSay(0, "HTTP Error " + (string)status + ": " + body + " - Stopping polling");
                } else {
                    // Report error but we're not polling
                    llOwnerSay("HTTP Error " + (string)status + ": " + body);
                }
                return;
            }
        }
        
        if (425 == status) {
            // 425 means the response is not yet available from AI talkmaster
            return;
        } else if (0 == status) {
            // request Timeout in OpenSimulator: returns code 0 after 30 seconds
            return;
        } else if (499 == status) {
            // ignore 499 client timeouts, they occur frequently on OpenSimulator Community Conference grid
            return;
        } else if (200 == status) {
            // missed 200 (ID changed)
            return;
        } else {
            // Report all other status codes to owner
            llOwnerSay("HTTP Error " + (string)status + ": " + body);
        }
    }

    timer()
    {
        // Invoked after every pollFreq seconds.
        stopwatch=stopwatch+pollFreq;    
        float remaining = reserveTime + conversation_time - stopwatch;
        // If the remaining seconds have exhausted.
        if(remaining<=0.0) {
            llSay(0, "Thank you for being here today "+username+". The session is finished, click to start a fresh one");
            set_ready();
        } else {
            if (pollingResponse == 1) {
                if(conversation_key==""){
                    return;
                }
                // Check if polling has timed out
                float current_time = llGetUnixTime();
                if (current_time - polling_start_time > polling_timeout) {
                    llOwnerSay("Polling timeout reached (" + (string)polling_timeout + " seconds). Stopping polling for message");
                    pollingResponse = 0; // Stop polling
                    // Clear polling indicator
                    llSetText("Please click on me to start a new session.", <1.0, 1.0, 0.5>, 1.0);
                    llSay(0, "Sorry, the response took too long. Please try again.");
                    listener = llListen(com_channel, "", user, ""); // Resume listening
                    llListen(command_channel, "", user, "");
                    return;
                }
                conversation_getMessageResponse(conversation_key);
            }
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