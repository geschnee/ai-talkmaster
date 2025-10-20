// script by Herzstein Dev
// This script provides a way of interacting with the AI Talkmaster Generate functionality.
// When the user clicks the object, it sends the user's next message to the AI Talkmaster server and prints the response.
// More details at https://github.com/geschnee/ai-talkmaster

string ait_endpoint = "http://hg.hypergrid.net:6000";


integer listener;
string prompt;
key user=NULL_KEY;
string username ="";
float reserveTime = 600.0;
float pollFreq = 2.0;
float stopwatch;


// Validation variables
key modelsValidationId;
integer modelsValidated = 0;
integer validationInProgress = 0;

// Notecard completion tracking
integer notecardsCompleted = 0;
integer PARAMETERS_NOTECARD_COMPLETED = 1;
integer SYSTEM_NOTECARD_COMPLETED = 2;
integer ALL_NOTECARDS_COMPLETED = 3; // 1 + 2 = 3

integer max_response_length = 16384;

integer MAX_LENGTH = 1024;    // Maximum string length in LSL

// Polling timeout variables
float polling_start_time = 0.0;
float polling_timeout = 300.0; // Stop polling after 5 minutes


// Read Entire Notecard as Single String
string parametersNotecardName = "llm-parameters";
string systemNotecardName = "llm-system"; 
key parametersNotecardQueryId;
key systemNotecardQueryId;
integer parametersCurrentLine= 0;
integer systemCurrentLine = 0;
list systemNotecardLines = [];


string charactername;
string model;
string system;

string optionstring;
list optionStringParts=[];

list optionParameters = [
    "num_ctx", "repeat_last_n","repeat_penalty","temperature","seed","stop","num_predict","top_k","top_p","min_p"
];

// example notecard:
//name:Oracle
//model:llama3.2
//instructions:Talk like davy jones, the feared pirate. Talk like you are talking to an old and cherished rival.
//temperature:1
//num_predict:-1


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

start_optionstring() {
    optionstring = "{";
    optionStringParts = [];
}

add_option(string optionname, string value){
    if (optionname == "stop"){
        optionStringParts = optionStringParts + ["\"stop\": [\"" + value + "\"]"];
    } else {
        optionStringParts = optionStringParts + ["\""+optionname+"\": " + value];
    }
}

finish_optionstring(){
    string joins = llDumpList2String(optionStringParts, ", ");
    optionstring = "{ " + joins +" }";
}

call_oracle(string prompt, string username) {
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
    
    string system_instructions = llReplaceSubString(system, "\"", "\\\"", 0);
    string prompt_filtered = llReplaceSubString(prompt, "\"", "\\\"", 0);
    llHTTPRequest(ait_endpoint + "/generate/postMessage", [HTTP_METHOD, "POST", HTTP_BODY_MAXLENGTH, max_response_length, HTTP_MIMETYPE, "application/json"], "{
        \"username\": \""+username+"\",
        \"prompt\": \""+prompt_filtered+"\",
        \"model\": \"" + model + "\",
        \"system_instructions\": \"" + system_instructions + "\",
        \"options\": " + optionstring +"
    }");
}

call_response(string prompt, string username) {
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
    
    string system_instructions = llReplaceSubString(system, "\"", "\\\"", 0);
    string prompt_filtered = llReplaceSubString(prompt, "\"", "\\\"", 0);
    llHTTPRequest(ait_endpoint + "/generate/getMessageResponse", [HTTP_METHOD, "GET", HTTP_BODY_MAXLENGTH, max_response_length, HTTP_MIMETYPE, "application/json"], "{
        \"username\": \""+username+"\",
        \"prompt\": \""+prompt_filtered+"\",
        \"model\": \"" + model + "\",
        \"system_instructions\": \"" + system_instructions + "\",
        \"options\": " + optionstring +"
    }");
}

set_ready() {
    llListenRemove(listener);
    llSetTimerEvent(0);
    user=NULL_KEY;
    username="";
    prompt="";
    llSay(0, "Please click on me to start a new session.");
    llSay(0, "---");
    llSetTexture("AI-Box-01", ALL_SIDES);
}

string str_replace(string src, string from, string to)
{
    return llDumpList2String(llParseString2List(src, [from], []), to);
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
    if (model == "") {
        llOwnerSay("Error: Model parameter is missing. Cannot validate.");
        return;
    }
    
    llOwnerSay("Starting parameter validation...");
    validateModel(model);
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

        start_optionstring();
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

                string line = [data];

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
                    
                    integer listLength = llGetListLength(optionParameters);
                    integer i;
                    for (i=0; i< listLength; i++)
                    {
                        string indexName = llList2String(optionParameters, i);
                        if (paramName == indexName) 
                        {
                            add_option(paramName, value);
                        }
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
                
                finish_optionstring();
                llOwnerSay("optionstring: " + optionstring);
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

                string line = [data];

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
                
                // Now you have the entire notecard as a single string
                llOwnerSay("System notecard content loaded:");
                llOwnerSay("system: " + entireContent);

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
            llSay(0, "Error reading config. Please check that 'llm-parameters' and 'llm-system' notecards exist and contain valid data. Reset the script for more details.");
            return;
        }
        if (user!=NULL_KEY & llDetectedKey(0) != user) {
            llSay(0, "Sorry I am currently in use by " + llKey2Name(user) + ". Please await your turn." );
        } else {
            user = llDetectedKey(0);
            
            llSay(0, "Hello "+llKey2Name(user)+" I am made to forward your input to "+ charactername + ". I can deal only with one user at a time."); 
            username = llKey2Name(user);
            llSay(0, "Please enter something you want to say to "+ charactername + " in chat.");
            listener = llListen(0, "", user, "");
            stopwatch = 0;
            prompt="";
            llSetTexture("AI-Box-02", ALL_SIDES);
            llSetTimerEvent(pollFreq);
        }
    }

    listen(integer channel, string name, key id, string message)
    {
        if(channel == 0 && id == user) {
            stopwatch=0;
            prompt = message;
            polling_start_time = llGetUnixTime(); // Record when polling started
            call_oracle(message, username);
            llSay(0, "Message is sent.");
            llListenRemove(listener);
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
            

            string response = llJsonGetValue(body, ["response"]);

            string username_rtn = llJsonGetValue(body, ["username"]);
            string prompt_rtn = llJsonGetValue(body, ["prompt"]);
            if (username_rtn != username) {
                return;
            }
            if (prompt_rtn != prompt) {
                return;
            }


           

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


            llSay(0, "Thank you for being here today "+username+". Now a new session will be opened.");
            
            set_ready();
        } else if (425 == status) {
            // 425 means the response is not yet available from AI talkmaster
            return;
        } else if (0 == status) {
            // request Timeout in OpenSimulator: returns code 0 after 30 seconds
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
        float remaining = reserveTime - stopwatch;
        // If the remaining seconds have exhausted.
        if(remaining<=0.0) {
            llSay(0, "Sorry timed out. I shall restart now.");
            llSetTexture("AI-Box-04", ALL_SIDES);
            set_ready();
        } else {
            if (prompt != "") {
                // Check if polling has timed out
                float current_time = llGetUnixTime();
                if (current_time - polling_start_time > polling_timeout) {
                    llOwnerSay("Polling timeout reached (" + (string)polling_timeout + " seconds). Stopping polling for prompt: " + prompt);
                    prompt = ""; // Clear prompt to stop polling
                    llSay(0, "Sorry, the response took too long. Please try again.");
                    set_ready();
                    return;
                }
                call_response(prompt, username);
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