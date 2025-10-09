// script by Herzstein
// concet by Art Blue aka Reiner Schneeberger 
// version 0.1 2025-04-29

integer config_channel = 12345;

integer com_channel = 0; // Change this to any channel of your choice.
integer user_listener;
integer config_listener;
string prompt;
key user=NULL_KEY;
string username ="";
float reserveTime = 180.0;
float pollFreq = 2.0;
float stopwatch;

string ait_endpoint = "http://hg.hypergrid.net:7999";

// Validation variables
key modelsValidationId;
integer modelsValidated = 0;
integer validationInProgress = 0;

string conversation_key;
float conversation_time=0;
integer conversation_message_id= 0;
integer pollingResponse=0;

integer max_response_length = 16384;


float CONVERSATION_INCREMENT=60;

integer MAX_LENGTH = 1024;    // Maximum string length in LSL

string simulatorHostname;
string regionName;


integer configs_loaded;
key config_sender=NULL_KEY;
string agentName;
string model;
string system;

string optionstring;


// Function to split text into chunks
list splitText(string text)
{
    list chunks = [];
    integer textLength = llStringLength(text);
    
    // If text is already short enough, return it as a single chunk
    if (textLength <= MAX_LENGTH)
    {
        return [text];
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
                if (newlinePos==-1 && llGetSubString(text, i, i) == "\n")
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
                    if (spacePos == -1 && llGetSubString(text, i, i) == " ")
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
        chunks += [llGetSubString(text, currentPos, endPos - 1)];
        currentPos = endPos;
    }
    
    return chunks;
}

string deleteUpToSubstring(string input, string substring)
{
    integer position = llSubStringIndex(input, substring);
    
    if (position == -1) // Substring not found
        return input;
    
    return llDeleteSubString(input, 0, position + llStringLength(substring) - 1);
}

start_oracle(string username) {
    // Check if model validation has completed and failed
    if (validationInProgress == 0 && modelsValidated == 0) {
        llSay(0, "Model '" + model + "' is not available on the server. Please check the configuration.");
        return;
    }
    
    // If validation is still in progress, wait
    if (validationInProgress == 1) {
        llSay(0, "Model validation is still in progress. Please wait...");
        return;
    }
    
    string system_filtered = llReplaceSubString(system, "\"", "\\\"", 0);
    llHTTPRequest(ait_endpoint + "/conversation/start", [HTTP_METHOD, "POST", HTTP_BODY_MAXLENGTH, max_response_length, HTTP_MIMETYPE, "application/json"], "{
        \"username\": \""+username+"\",
        \"simulatorHostname\": \""+simulatorHostname+"\",
        \"regionName\": \""+regionName+"\",
        \"model\": \"" + model + "\",
        \"system\": \"" + system_filtered +"\",
        \"options\": " + optionstring +"
    }");
}

call_oracle(string conversation_key, integer message_id, string prompt) {
    // Check if model validation has completed and failed
    if (validationInProgress == 0 && modelsValidated == 0) {
        llSay(0, "Model '" + model + "' is not available on the server. Please check the configuration.");
        return;
    }
    
    // If validation is still in progress, wait
    if (validationInProgress == 1) {
        llSay(0, "Model validation is still in progress. Please wait...");
        return;
    }
    
    string prompt_filtered = llReplaceSubString(prompt, "\"", "\\\"", 0);
    llHTTPRequest(ait_endpoint + "/conversation/sendMessage", [HTTP_METHOD, "POST", HTTP_BODY_MAXLENGTH, max_response_length, HTTP_MIMETYPE, "application/json"], "{
        \"conversation_key\": \""+conversation_key+"\",
        \"prompt\": \""+prompt_filtered+"\",
        \"simulatorHostname\": \""+simulatorHostname+"\",
        \"regionName\": \""+regionName+"\",
        \"message_id\": "+message_id+ "
    }");
}

call_response(string conversation_key, integer message_id) {
    llHTTPRequest(ait_endpoint + "/conversation/getMessageResponse", [HTTP_METHOD, "GET", HTTP_BODY_MAXLENGTH, max_response_length, HTTP_MIMETYPE, "application/json"], "{
        \"conversation_key\": \""+conversation_key+"\",
        \"simulatorHostname\": \""+simulatorHostname+"\",
        \"regionName\": \""+regionName+"\",
        \"message_id\": "+message_id+"
    }");
}

set_ready() {
    llListenRemove(user_listener);
    llListenRemove(config_listener);
    llSetTimerEvent(0);
    user=NULL_KEY;
    username="";
    prompt="";


    config_sender=NULL_KEY;
    configs_loaded=0;
    agentName=NULL_KEY;
    system=NULL_KEY;
    model=NULL_KEY;
    optionstring=NULL_KEY;

    llSay(0, "Please click on me to start a new session.");
    llSay(0, "---");
    llSetTexture("AI-Box-01", ALL_SIDES);
}

string str_replace(string src, string from, string to)
{
    return llDumpList2String(llParseString2List(src, [from], []), to);
}

// Function to validate model against /models endpoint
validateModel(string modelToValidate)
{
    if (validationInProgress) {
        llOwnerSay("Validation already in progress, please wait...");
        return;
    }
    
    validationInProgress = 1;
    llOwnerSay("Validating model: " + modelToValidate);
    modelsValidationId = llHTTPRequest(ait_endpoint + "/models", 
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
    if (model == "") {
        llOwnerSay("Error: Model parameter is missing. Cannot validate.");
        return;
    }
    
    llOwnerSay("Starting parameter validation...");
    validateModel(model);
}

start_conversation() {
    llSay(0, "Hello "+llKey2Name(user)+" I am made to forward your input to "+ agentName + "."); 
    user_listener = llListen(com_channel, "", user, "");

    stopwatch = 0;
    prompt="";
    llSetTexture("AI-Box-02", ALL_SIDES);

    conversation_key="";
    llSetTexture("AI-Box-02", ALL_SIDES);

    start_oracle(username);
}

default
{
    state_entry()
    {
        set_ready();
        simulatorHostname = llGetSimulatorHostname();
        regionName = llGetRegionName();
    }

    touch_start(integer num_detected)
    {
        if (user!=NULL_KEY & llDetectedKey(0) != user) {
            llSay(0, "Sorry I am currently in use by " + llKey2Name(user) + ". Please await your turn." );
        } else if (configs_loaded==0){
            user = llDetectedKey(0);
            username = llKey2Name(user);
            
            llSay(0, "Hello "+ llKey2Name(user) + ", I am now waiting for config information on channel "+config_channel +" by Inputter object.");
            stopwatch = 0;

            config_listener = llListen(config_channel, "", NULL_KEY, "");

            llSetTexture("AI-Box-02", ALL_SIDES);
            llSetTimerEvent(pollFreq);
        }
    }

    listen(integer channel, string name, key id, string message)
    {
        //llSay(0, "recieved on channel " + channel + " by " + name + " message: " + message);

        if (user==NULL_KEY){
            return;
        }
        if(channel == config_channel && id != user) {
            if (configs_loaded==1){
                return;
            }
            if (config_sender==NULL_KEY) {
                config_sender=id;
                //llSay(0, "config_sender: " + config_sender);
            }
            if (config_sender!=id){
                llSay(0, "Recieved configs from multiple objects, please move objects out of whisper range on channel "+ config_channel);
                return;
            }
            integer index = llSubStringIndex(message, ":");
            if(index == -1){
                return;
            }
            string paramName = llGetSubString(message, 0, index - 1);
            string paramValue = deleteUpToSubstring(message, ":");
            if (paramName=="llmConfig_agentName"){
                agentName=paramValue;
            }
            if (paramName=="llmConfig_model"){
                model=paramValue;
            }
            if (paramName=="llmConfig_system"){
                system=paramValue;
            }
            if (paramName=="llmConfig_optionstring"){
                optionstring=paramValue;
            }

            if (agentName!=NULL_KEY && model!=NULL_KEY && system!=NULL_KEY && optionstring!=NULL_KEY){
                configs_loaded=1;
                //llSay(0, "Configs have been recieved: ");
                //llSay(0, "agentName: " + agentName);
                //llSay(0, "system: " + system);
                //llSay(0, "model: " + model);
                //llSay(0, "optionstring: " + optionstring);

                // Validate parameters before starting conversation
                validateAllParameters();
                
                start_conversation();
            }

        }

        if(conversation_key==""){
            return;
        }

        if(message=="quit session" && id == user) {
            llSay(0, "Thank you for being here today "+username+". The session is finished, click to start a fresh one");
            llSetTexture("AI-Box-04", ALL_SIDES);
            set_ready();
        }
        if(channel == com_channel && id == user) {
            stopwatch=0;
            prompt = message;
            conversation_message_id = conversation_message_id + 1;
            call_oracle(conversation_key, conversation_message_id, prompt);
            llSay(0, "Message is sent.");
            pollingResponse=1;
            llListenRemove(user_listener);
        }   
    }

    http_response(key request_id, integer status, list metadata, string body)
    {
        // Handle validation responses
        if (request_id == modelsValidationId) {
            if (status == 200) {
                llOwnerSay("Models validation response received");
                string chatModels = llJsonGetValue(body, ["chat_models"]);
                if (isValueInJsonArray(chatModels, model)) {
                    llOwnerSay("✓ Model '" + model + "' is valid");
                    modelsValidated = 1;
                } else {
                    llOwnerSay("✗ Model '" + model + "' is NOT valid. Available models: " + chatModels);
                    modelsValidated = 0;
                }
                
                validationInProgress = 0;
            } else {
                llOwnerSay("Error validating model: HTTP " + (string)status + " - " + body);
                validationInProgress = 0;
            }
            return;
        }
        
        if(200 == status) {
            if (username == ""){
                //llSay(0, "reset was called between request and response");
                return;
            }
            string local_conversation_key = llJsonGetValue(body, ["conversation_key"]);
           
            if (local_conversation_key != conversation_key){
                conversation_key = local_conversation_key;
                llSay(0, "Please enter something you want to say to " + agentName + " in chat.");
                // new conversation was started on backend
                conversation_time=0;
                conversation_message_id=0;
                pollingResponse=0;

                user_listener = llListen(com_channel, "", user, "");
                return;
            }

            
            string message_id = llJsonGetValue(body, ["message_id"]);
            if (message_id!=(string) conversation_message_id){
                return;
            }

            // start listening to user messages again
            pollingResponse=0;
            user_listener = llListen(com_channel, "", user, "");
            conversation_time = conversation_time + CONVERSATION_INCREMENT;


            string response = llJsonGetValue(body, ["response"]);
            
            string trimmed_response = deleteUpToSubstring(response, "</think>");
            trimmed_response = llStringTrim(trimmed_response, STRING_TRIM);

            llSay(0, username+" that's for you: ");

            list chunks = splitText(trimmed_response);
            integer i;
            for (i = 0; i < llGetListLength(chunks); ++i)
            {
                string chunk = llList2String(chunks, i);
                integer i_plus = i + 1;
                llSay(0, i_plus + " " + chunk);
            }

            
            
            
        } else if (202 == status) {
            // "Waiting for result to be availible"
            return;
        } else if (400 == status) {
            llSay(0, body);
            return;
        } else if (499 == status) {
            llSay(0, "Connection refused, please contact script creator.");
            return;
        } else {
            // we can ignore the other failed responses, since they are caused by llHTTPRequest TimeOut
            return;
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
            llSetTexture("AI-Box-04", ALL_SIDES);
            set_ready();
        } else {
            if (pollingResponse == 1) {
                if(conversation_key==""){
                    return;
                }
                call_response(conversation_key, conversation_message_id);
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