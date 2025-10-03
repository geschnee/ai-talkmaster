


integer config_channel = 12345; // Change this to any channel of your choice.
integer listener;
float sendFreq = 2.0;


// Read Entire Notecard as Single String
string notecardName = "llm-instructions";  // Change this to your notecard name
key notecardQueryId;
integer currentLine = 0;
list notecardLines = [];


string agentName="";
string model="";
string system="";

string optionstring="";
list optionStringParts=[];

list optionParameters = [
    "num_ctx", "repeat_last_n","repeat_penalty","temperature","seed","stop","num_predict","top_k","top_p","min_p"
];

// example notecard:
//agentName:Oracle
//model:llama3.2
//instructions:Talk like davy jones, the feared pirate. Talk like you are talking to an old and cherished rival.
//temperature:1
//num_predict:-1


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

default
{
    state_entry()
    {
        // Verify the notecard exists
        if (llGetInventoryType(notecardName) != INVENTORY_NOTECARD)
        {
            llOwnerSay("Error: Notecard '" + notecardName + "' not found.");
            return;
        }
        // Start reading the notecard from the first line

        start_optionstring();
        notecardQueryId = llGetNotecardLine(notecardName, currentLine);
    }

    dataserver(key query_id, string data)
    {
        if (query_id == notecardQueryId)
        {
            if (data != EOF)
            {
                string line = [data];

                list splits = llParseString2List(line, [":"],[]);
                
                if ( llGetListLength(splits) == 2 ) 
                {
                    string paramName = llList2String(splits, 0);
                    string value = llList2String(splits, 1);

                    if (paramName == "agentName") 
                    {
                        agentName = value;
                    }
                    if (paramName == "model") 
                    {
                        model = value;
                    }
                    if (paramName == "system") 
                    {
                        system = value;
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

                // Add this line to our collection
                notecardLines += line;
                
                // Get the next line
                currentLine++;
                notecardQueryId = llGetNotecardLine(notecardName, currentLine);
            }
            else
            {
                // We've reached the end of the notecard
                // Combine all lines into a single string with newlines
                string entireContent = llDumpList2String(notecardLines, "\n");
                
                // Now you have the entire notecard as a single string
                llOwnerSay("Notecard content loaded:");

                if (agentName=="") {
                    llSay(0, "Invalid: empty agentName");
                    return;
                }
                if (model=="") {
                    llSay(0, "Invalid: empty model");
                    return;
                }

                llOwnerSay("agentName: " + agentName);
                llOwnerSay("model: " + model);
                llOwnerSay("system: " + system);
                
                finish_optionstring();
                llOwnerSay("optionstring: " + optionstring);

                llOwnerSay("This Inputter send on channel "+config_channel + " every "+ sendFreq + " seconds.");
                
                llSetTimerEvent(sendFreq);
                
            }
        }
    }

    timer()
    {
        llWhisper(config_channel, "llmConfig_agentName:"+agentName);
        llWhisper(config_channel, "llmConfig_model:"+model);
        llWhisper(config_channel, "llmConfig_system:"+system);
        llWhisper(config_channel, "llmConfig_optionstring:"+optionstring);
    }

    // If changes are done to object inventory then reset the script.
    changed(integer a)
    {
        if(a & CHANGED_INVENTORY ) {
            llResetScript();
        }
    }
}