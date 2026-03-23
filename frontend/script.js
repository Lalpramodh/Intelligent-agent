const API_ENDPOINT='/api/agent';
const API_HEALTH_ENDPOINT='/api/health';
const API_BASE_URL=window.__API_BASE_URL__||getApiBaseUrl();
const runButton=document.getElementById('runAgentBtn');
const userQueryInput=document.getElementById('userQuery');
const loadingOverlay=document.getElementById('loadingOverlay');
const summaryContainer=document.getElementById('summaryContent');
const parsedContainer=document.getElementById('parsedContent');
const apiResultsContainer=document.getElementById('apiResults');
const decisionLogicContainer=document.getElementById('decisionLogic');
const flowDiagramContainer=document.getElementById('flowDiagram');
const validationContainer=document.getElementById('validationContent');
const warningsContainer=document.getElementById('warningsContent');
const failureHandlingContainer=document.getElementById('failureHandling');
const statusBadge=document.querySelector('.status-badge');
const statusLabel=document.querySelector('.status-badge span:last-child');
window.demoMode=new URLSearchParams(window.location.search).get('demo')==='1';

function getApiBaseUrl(){
    if(window.location.protocol==='file:'){return 'http://localhost:5000';}
    if(['localhost','127.0.0.1'].includes(window.location.hostname)&&window.location.port&&window.location.port!=='5000'){
        return `${window.location.protocol}//${window.location.hostname}:5000`;
    }
    return window.location.origin;
}

if(runButton){runButton.addEventListener('click',handleRunAgent);}
document.querySelectorAll('.example-chip').forEach((chip)=>{
    chip.addEventListener('click',()=>{
        if(userQueryInput){userQueryInput.value=chip.getAttribute('data-query')||'';}
        handleRunAgent();
    });
});
if(userQueryInput){
    userQueryInput.addEventListener('keydown',(event)=>{
        if((event.ctrlKey||event.metaKey)&&event.key==='Enter'){handleRunAgent();}
    });
}

init();

async function init(){
    setConnectionStatus('connecting','Checking Backend');
    const online=await checkBackendConnection();
    if(window.demoMode&&!online){
        setConnectionStatus('connecting','Demo Mode');
        showMockData();
    }
}

async function checkBackendConnection(){
    try{
        const response=await fetch(`${API_BASE_URL}${API_HEALTH_ENDPOINT}`,{headers:{Accept:'application/json'}});
        if(!response.ok){throw new Error(`Health check failed: ${response.status}`);}
        setConnectionStatus('online','Backend Connected');
        return true;
    }catch(error){
        console.warn('Backend health check failed:',error);
        setConnectionStatus('offline','Backend Offline');
        return false;
    }
}

async function handleRunAgent(){
    const userQuery=userQueryInput?.value.trim();
    if(!userQuery){
        showError('Please enter a scheduling request.');
        return;
    }
    setLoadingState(true);
    clearResults();
    try{
        const response=await fetch(`${API_BASE_URL}${API_ENDPOINT}`,{
            method:'POST',
            headers:{'Content-Type':'application/json',Accept:'application/json'},
            body:JSON.stringify({query:userQuery})
        });
        const payload=await readJson(response);
        if(!payload){throw new Error(`The backend returned status ${response.status} without valid JSON.`);}
        renderResponse(normalizeAgentResponse(payload));
        setConnectionStatus('online','Backend Connected');
        if(!response.ok&&response.status>=500){showError(payload.message||`Backend error (${response.status}).`);}
    }catch(error){
        console.error('Error calling backend:',error);
        setConnectionStatus('offline','Backend Unreachable');
        showError(createConnectionErrorMessage(error));
        simulateFailureHandling(error);
    }finally{
        setLoadingState(false);
    }
}

async function readJson(response){
    try{return await response.json();}catch(error){return null;}
}

function setLoadingState(isLoading){
    if(loadingOverlay){loadingOverlay.classList.toggle('active',isLoading);}
    if(runButton){
        runButton.disabled=isLoading;
        runButton.style.opacity=isLoading?'0.75':'1';
        runButton.style.cursor=isLoading?'wait':'pointer';
    }
}

function clearResults(){
    [
        summaryContainer,parsedContainer,apiResultsContainer,decisionLogicContainer,
        flowDiagramContainer,validationContainer,warningsContainer,failureHandlingContainer
    ].forEach((container)=>{
        if(container){
            container.innerHTML='';
            container.style.opacity='1';
        }
    });
}

function renderResponse(data){
    updateSummary(data.summary);
    updateParsedRequest(data.parsed_request);
    updateAPIResults(data.api_results);
    updateDecisionLogic(data.decision_logic);
    updateFlowDiagram(data.flow_diagram);
    updateValidation(data.validation);
    updateWarnings(data.warnings);
    updateFailureHandling(data.failure_handling);
}

function normalizeAgentResponse(data){
    const status=data?.status||'error';
    const message=data?.message||'No response message received.';
    return {
        status,
        message,
        summary:normalizeSummary(data?.summary,status,message),
        parsed_request:normalizeParsedRequest(data?.parsed_request),
        api_results:normalizeApiResults(data?.api_results),
        decision_logic:normalizeDecisionLogic(data?.decision_logic),
        flow_diagram:normalizeFlowDiagram(data?.flow_diagram),
        validation:normalizeValidation(data?.validation),
        warnings:normalizeWarnings(data?.warnings,data?.recommendations),
        failure_handling:normalizeFailureHandling(data?.failure_handling,status)
    };
}

function normalizeSummary(summary,status,message){
    const details=[];
    pushDetail(details,'Outcome',summary?.outcome);
    pushDetail(details,'Requested Slot',summary?.requested_slot);
    pushDetail(details,'Recommended Action',summary?.recommended_action);
    pushDetail(details,'Weather Risk',formatLabel(summary?.weather_risk));
    pushDetail(details,'CRM Reference',summary?.crm_reference);
    return {decision:formatStatusLabel(status),message,timestamp:summary?.timestamp||null,details,tone:getStatusTone(status)};
}

function normalizeParsedRequest(parsed){
    const fields=[];
    if(!parsed||typeof parsed!=='object'){return {fields};}
    pushDetail(fields,'Intent',formatLabel(parsed.intent));
    pushDetail(fields,'Client',parsed.client_name||parsed.attendee);
    pushDetail(fields,'Date',formatDateValue(parsed.date));
    pushDetail(fields,'Time',formatTimeValue(parsed.time));
    pushDetail(fields,'City',parsed.city||parsed.location);
    pushDetail(fields,'Extraction',parsed.extraction_method);
    return {fields};
}

function normalizeApiResults(apiResults){
    const items=[];
    if(!apiResults||typeof apiResults!=='object'){return {items};}
    if(apiResults.calendar){
        const calendar=apiResults.calendar;
        const details=[];
        if(calendar.message){details.push(calendar.message);}
        pushTextDetail(details,'Requested slot',calendar.requested_slot?.display||calendar.slots);
        pushTextDetail(details,'Next available',calendar.next_available?.display);
        if(Array.isArray(calendar.busy_slots)&&calendar.busy_slots.length){pushTextDetail(details,'Busy slots',calendar.busy_slots.join(', '));}
        if(Array.isArray(calendar.alternatives)&&calendar.alternatives.length){
            pushTextDetail(details,'Alternatives',calendar.alternatives.map((slot)=>slot.display).join(', '));
        }
        items.push({title:'Calendar Check',icon:'fa-calendar-check',statusClass:mapApiStatusToClass(calendar.status,calendar.available),details});
    }
    if(apiResults.weather){
        const weather=apiResults.weather;
        const details=[];
        if(weather.advisory||weather.message){details.push(weather.advisory||weather.message);}
        pushTextDetail(details,'City',weather.city);
        pushTextDetail(details,'Condition',weather.condition);
        pushTextDetail(details,'Risk level',formatLabel(weather.risk_level));
        const temperature=weather.temperature_c??weather.temperature;
        if(temperature!==undefined&&temperature!==null){pushTextDetail(details,'Temperature',`${temperature}${typeof temperature==='number'?'°C':''}`);}
        pushTextDetail(details,'Fallback detail',weather.error);
        items.push({title:'Weather Forecast',icon:'fa-cloud-sun',statusClass:mapApiStatusToClass(weather.status),details});
    }
    if(apiResults.crm){
        const crm=apiResults.crm;
        const details=[];
        if(crm.message){details.push(crm.message);}
        pushTextDetail(details,'Meeting ID',crm.meeting_id);
        pushTextDetail(details,'Client',crm.client_name||crm.contact_info);
        const scheduledFor=crm.scheduled_for?`${formatDateValue(crm.scheduled_for.date)} at ${formatTimeValue(crm.scheduled_for.time)} in ${crm.scheduled_for.city}`:null;
        pushTextDetail(details,'Scheduled for',scheduledFor);
        items.push({title:'CRM Check',icon:'fa-address-card',statusClass:mapApiStatusToClass(crm.status),details});
    }
    return {items};
}

function normalizeDecisionLogic(logic){
    if(logic&&Array.isArray(logic.steps)){return logic;}
    return {steps:Array.isArray(logic)?logic.map((entry,index)=>({title:`Step ${index+1}`,description:entry,completed:true})):[]};
}

function normalizeFlowDiagram(flow){
    if(flow&&Array.isArray(flow.nodes)){return flow;}
    if(!Array.isArray(flow)){return {nodes:[]};}
    const nodeNames=[];
    flow.forEach((entry)=>{
        String(entry).split('->').map((part)=>part.trim()).filter(Boolean).forEach((part)=>{
            if(!nodeNames.includes(part)){nodeNames.push(part);}
        });
    });
    return {nodes:nodeNames.map((name,index)=>({name,status:describeFlowStatus(index,nodeNames.length),icon:inferFlowIcon(name)}))};
}

function normalizeValidation(validation){
    return {
        checks:Array.isArray(validation?.checks)
            ?validation.checks.map((check)=>({
                name:formatLabel(check.name),
                message:check.message||check.detail||'Validation step completed.',
                passed:Boolean(check.passed)
            }))
            :[]
    };
}

function normalizeWarnings(warnings,recommendations){
    if(warnings&&typeof warnings==='object'&&!Array.isArray(warnings)){
        return {
            warnings:Array.isArray(warnings.warnings)?warnings.warnings:[],
            recommendations:Array.isArray(warnings.recommendations)?warnings.recommendations:[]
        };
    }
    return {
        warnings:Array.isArray(warnings)?warnings:[],
        recommendations:Array.isArray(recommendations)?recommendations:[]
    };
}

function normalizeFailureHandling(failureHandling,status){
    if(failureHandling&&!Array.isArray(failureHandling)){
        return {
            strategy:failureHandling.strategy||defaultFailureStrategy(status),
            retry_count:failureHandling.retry_count||null,
            fallback:failureHandling.fallback||null,
            steps:Array.isArray(failureHandling.steps)?failureHandling.steps:[]
        };
    }
    const steps=Array.isArray(failureHandling)?failureHandling:[];
    return {
        strategy:steps[0]||defaultFailureStrategy(status),
        retry_count:extractRetryCount(steps),
        fallback:steps.find((step)=>/fallback|manual/i.test(step))||null,
        steps
    };
}

function updateSummary(summary){
    if(!summaryContainer){return;}
    if(!summary){
        summaryContainer.innerHTML=`<div class="placeholder"><i class="fas fa-hourglass-half"></i><p>No data yet</p><span>Submit a query to see the scheduling decision</span></div>`;
        return;
    }
    const detailsHtml=summary.details.length?`<div class="summary-meta">${summary.details.map((detail)=>`<div class="summary-meta-item"><strong>${detail.label}:</strong> ${detail.value}</div>`).join('')}</div>`:'';
    summaryContainer.innerHTML=`<div class="summary-item"><div class="summary-panel ${summary.tone}"><i class="fas fa-check-circle" style="font-size:24px;margin-bottom:12px;display:inline-block;"></i><h4 style="margin-bottom:8px;">Decision: ${summary.decision}</h4><p style="font-size:0.875rem;opacity:0.95;">${summary.message||'Processing completed.'}</p>${summary.timestamp?`<small style="display:block;margin-top:12px;"><i class="fas fa-clock"></i> ${new Date(summary.timestamp).toLocaleString()}</small>`:''}${detailsHtml}</div></div>`;
}

function updateParsedRequest(parsed){
    if(!parsedContainer){return;}
    if(!parsed||!parsed.fields.length){
        parsedContainer.innerHTML=`<div class="placeholder"><i class="fas fa-spinner fa-pulse"></i><p>Awaiting input...</p></div>`;
        return;
    }
    parsedContainer.innerHTML=`<div class="parsed-details">${parsed.fields.map((field)=>`<div class="detail-item"><strong><i class="fas fa-circle-info"></i> ${field.label}:</strong> ${field.value}</div>`).join('')}</div>`;
}

function updateAPIResults(apiResults){
    if(!apiResultsContainer){return;}
    if(!apiResults||!apiResults.items.length){
        apiResultsContainer.innerHTML=`<div class="placeholder"><i class="fas fa-cloud-sun"></i><p>Calendar, weather, and CRM outputs will render here</p></div>`;
        return;
    }
    apiResultsContainer.innerHTML=`<div class="api-results-list">${apiResults.items.map((item)=>`<div class="api-item ${item.statusClass}"><h4><i class="fas ${item.icon}"></i> ${item.title}</h4><div class="api-details">${item.details.map((detail)=>`<div class="api-detail-line">${detail}</div>`).join('')}</div></div>`).join('')}</div>`;
}

function updateDecisionLogic(logic){
    if(!decisionLogicContainer){return;}
    if(!logic||!logic.steps.length){
        decisionLogicContainer.innerHTML=`<div class="placeholder"><i class="fas fa-git-merge"></i><p>Decision steps will appear after processing</p></div>`;
        return;
    }
    decisionLogicContainer.innerHTML=`<div class="decision-steps">${logic.steps.map((step,index)=>`<div class="decision-step ${step.completed?'completed':''}"><div class="decision-step-icon">${step.completed?'<i class="fas fa-check"></i>':index+1}</div><div class="decision-step-content"><div class="decision-step-title">${step.title}</div><div class="decision-step-desc">${step.description}</div></div></div>`).join('')}</div>`;
}

function updateFlowDiagram(flow){
    if(!flowDiagramContainer){return;}
    if(!flow||!flow.nodes.length){
        flowDiagramContainer.innerHTML=`<div class="placeholder"><i class="fas fa-project-diagram"></i><p>End-to-end API flow visualization</p></div>`;
        return;
    }
    flowDiagramContainer.innerHTML=`<div class="flow-container">${flow.nodes.map((node)=>`<div class="flow-node"><div class="flow-icon"><i class="fas ${node.icon||'fa-circle'}"></i></div><div class="flow-content"><strong>${node.name}</strong><div style="font-size:0.875rem;color:var(--gray);">${node.status}</div></div></div>`).join('')}</div>`;
}

function updateValidation(validation){
    if(!validationContainer){return;}
    if(!validation||!validation.checks.length){
        validationContainer.innerHTML=`<div class="placeholder"><i class="fas fa-shield-alt"></i><p>Validation checks will appear here</p></div>`;
        return;
    }
    validationContainer.innerHTML=`<div class="validation-checks">${validation.checks.map((check)=>`<div style="display:flex;align-items:center;gap:12px;padding:12px;margin-bottom:8px;background:#f7fafc;border-radius:8px;"><i class="fas ${check.passed?'fa-check-circle':'fa-times-circle'}" style="color:${check.passed?'var(--success)':'var(--danger)'};"></i><div><strong>${check.name}</strong><div style="font-size:0.875rem;color:var(--gray);">${check.message}</div></div></div>`).join('')}</div>`;
}

function updateWarnings(warnings){
    if(!warningsContainer){return;}
    if(!warnings||(!warnings.warnings.length&&!warnings.recommendations.length)){
        warningsContainer.innerHTML=`<div class="placeholder"><i class="fas fa-info-circle"></i><p>No warnings or recommendations yet</p></div>`;
        return;
    }
    let html='';
    if(warnings.warnings.length){
        html+='<div class="warnings-list"><h4 style="margin-bottom:12px;">Warnings</h4>';
        warnings.warnings.forEach((warning)=>{html+=`<div class="warning-item"><div class="warning-icon"><i class="fas fa-exclamation-triangle"></i></div><div>${warning}</div></div>`;});
        html+='</div>';
    }
    if(warnings.recommendations.length){
        html+='<div class="recommendations-list" style="margin-top:16px;"><h4 style="margin-bottom:12px;">Recommendations</h4>';
        warnings.recommendations.forEach((recommendation)=>{html+=`<div class="recommendation-item"><div class="recommendation-icon"><i class="fas fa-lightbulb"></i></div><div>${recommendation}</div></div>`;});
        html+='</div>';
    }
    warningsContainer.innerHTML=html;
}

function updateFailureHandling(failure){
    if(!failureHandlingContainer){return;}
    if(!failure){
        failureHandlingContainer.innerHTML=`<div class="placeholder"><i class="fas fa-tools"></i><p>Backend failure handling approach will appear here</p></div>`;
        return;
    }
    const stepsHtml=Array.isArray(failure.steps)&&failure.steps.length?`<div class="failure-steps">${failure.steps.map((step)=>`<div class="failure-step">${step}</div>`).join('')}</div>`:'';
    failureHandlingContainer.innerHTML=`<div class="failure-details"><div style="background:#fee;padding:16px;border-radius:12px;border-left:4px solid var(--danger);"><strong><i class="fas fa-shield-virus"></i> Failure Handling Strategy:</strong><p style="margin-top:8px;">${failure.strategy||'Graceful degradation with retry mechanism.'}</p>${failure.retry_count?`<small>Retry attempts: ${failure.retry_count}</small>`:''}${failure.fallback?`<div style="margin-top:12px;"><strong>Fallback:</strong> ${failure.fallback}</div>`:''}${stepsHtml}</div></div>`;
}

function simulateFailureHandling(error){
    updateFailureHandling({
        strategy:'The frontend could not complete the backend request, so the workflow switched to connection recovery guidance.',
        retry_count:3,
        fallback:'Start the Flask backend and retry the request. If you only want a UI preview, open the page with ?demo=1.',
        steps:[
            `Checked endpoint: ${API_BASE_URL}${API_ENDPOINT}`,
            createConnectionErrorMessage(error),
            'Confirm the backend server is running and reachable on the expected host and port.',
            'Retry once the health check reports that the backend is connected.'
        ]
    });
}

function showError(message){
    const errorDiv=document.createElement('div');
    errorDiv.style.cssText='position:fixed;bottom:20px;right:20px;background:var(--danger);color:white;padding:12px 20px;border-radius:8px;z-index:2000;animation:slideIn 0.3s ease;box-shadow:0 4px 12px rgba(0,0,0,0.15);';
    errorDiv.innerHTML=`<i class="fas fa-exclamation-circle"></i> ${message}`;
    document.body.appendChild(errorDiv);
    setTimeout(()=>{
        errorDiv.style.animation='slideOut 0.3s ease';
        setTimeout(()=>errorDiv.remove(),300);
    },3500);
}

function setConnectionStatus(state,label){
    if(!statusBadge||!statusLabel){return;}
    statusBadge.classList.remove('online','offline','connecting');
    statusBadge.classList.add(state);
    statusLabel.textContent=label;
}

function createConnectionErrorMessage(error){
    const endpoint=`${API_BASE_URL}${API_ENDPOINT}`;
    if(error instanceof TypeError||/fetch|network/i.test(error.message)){return `Unable to reach the backend at ${endpoint}.`;}
    return error.message||'Unable to complete the request.';
}

function pushDetail(target,label,value){if(value){target.push({label,value});}}
function pushTextDetail(target,label,value){if(value){target.push(`${label}: ${value}`);}}
function formatStatusLabel(status){return status==='success'?'Success':status==='partial_success'?'Partial Success':status==='fail'?'Needs Attention':'Error';}
function getStatusTone(status){return status==='success'?'success':status==='error'?'error':'warning';}
function mapApiStatusToClass(status,available){return status==='degraded'||status==='partial_success'?'warning':status==='fail'||status==='error'||available===false?'error':'success';}
function formatDateValue(value){
    if(!value){return null;}
    if(/^\d{4}-\d{2}-\d{2}$/.test(value)){return new Date(`${value}T00:00:00`).toLocaleDateString(undefined,{day:'2-digit',month:'short',year:'numeric'});}
    return value;
}
function formatTimeValue(value){
    if(!value){return null;}
    if(/^\d{2}:\d{2}$/.test(value)){
        const [hours,minutes]=value.split(':');
        const parsedDate=new Date();
        parsedDate.setHours(Number(hours),Number(minutes),0,0);
        return parsedDate.toLocaleTimeString([],{hour:'2-digit',minute:'2-digit'});
    }
    return value;
}
function formatLabel(value){return value?String(value).replace(/_/g,' ').replace(/\b\w/g,(char)=>char.toUpperCase()):null;}
function describeFlowStatus(index,total){return index===0?'Initiated':index===total-1?'Rendered':'Processed';}
function inferFlowIcon(name){
    const normalized=name.toLowerCase();
    if(normalized.includes('frontend')){return 'fa-desktop';}
    if(normalized.includes('post')||normalized.includes('request')){return 'fa-paper-plane';}
    if(normalized.includes('parser')||normalized.includes('language')){return 'fa-language';}
    if(normalized.includes('calendar')){return 'fa-calendar';}
    if(normalized.includes('weather')){return 'fa-cloud-sun';}
    if(normalized.includes('crm')){return 'fa-address-card';}
    if(normalized.includes('validator')||normalized.includes('validation')){return 'fa-shield-alt';}
    if(normalized.includes('backend')||normalized.includes('api')||normalized.includes('flask')){return 'fa-server';}
    if(normalized.includes('decision')){return 'fa-brain';}
    if(normalized.includes('exception')||normalized.includes('error')){return 'fa-exclamation-triangle';}
    if(normalized.includes('response')||normalized.includes('output')){return 'fa-reply';}
    return 'fa-circle';
}
function defaultFailureStrategy(status){return status==='partial_success'?'The request completed partially, so a manual follow-up step is still required.':status==='fail'?'The workflow stopped safely after a validation or downstream check failed.':'Graceful degradation keeps the UI stable even when the backend cannot finish the request.';}
function extractRetryCount(steps){
    for(const step of steps){
        const match=String(step).match(/(\d+)\s+attempt/);
        if(match){return Number(match[1]);}
    }
    return null;
}

const animationStyle=document.createElement('style');
animationStyle.textContent='@keyframes slideIn{from{transform:translateX(100%);opacity:0;}to{transform:translateX(0);opacity:1;}}@keyframes slideOut{from{transform:translateX(0);opacity:1;}to{transform:translateX(100%);opacity:0;}}';
document.head.appendChild(animationStyle);

function showMockData(){
    const mockDate=new Date(Date.now()+24*60*60*1000).toISOString().slice(0,10);
    renderResponse(normalizeAgentResponse({
        status:'success',
        message:'Successfully scheduled meeting with Priya for tomorrow at 4 PM in Hyderabad.',
        summary:{outcome:'Meeting scheduled successfully.',requested_slot:'24 Mar 2026, 04:00 PM',recommended_action:'Confirm the meeting with Priya.'},
        parsed_request:{intent:'schedule',client_name:'Priya',date:mockDate,time:'16:00',city:'Hyderabad',extraction_method:'demo'},
        api_results:{
            calendar:{status:'success',available:true,message:'The requested calendar slot is available.',requested_slot:{display:'24 Mar 2026, 04:00 PM'},next_available:{display:'24 Mar 2026, 05:00 PM'}},
            weather:{status:'success',city:'Hyderabad',condition:'Clear',risk_level:'low',temperature_c:28,advisory:'Current weather is Clear; no weather-based scheduling block was detected.'},
            crm:{status:'success',meeting_id:'CRM-DEMO1234',client_name:'Priya',scheduled_for:{date:mockDate,time:'16:00',city:'Hyderabad'},message:'Meeting logged successfully in CRM.'}
        },
        decision_logic:[
            'Parsed the request with the demo extraction path.',
            'The requested calendar slot is available.',
            'Weather validation found Clear conditions with low risk in Hyderabad.',
            'The meeting was logged successfully in CRM, so the scheduling workflow completed.'
        ],
        flow_diagram:[
            'Frontend -> POST /api/agent',
            'POST /api/agent -> Request parser',
            'Request parser -> Calendar availability API',
            'Calendar availability API -> Weather API',
            'Weather API -> CRM logging API',
            'CRM logging API -> Frontend'
        ],
        validation:{checks:[
            {name:'response_status',detail:'Response status uses an expected lifecycle value.',passed:true},
            {name:'summary_object',detail:'Summary payload is a JSON object.',passed:true},
            {name:'api_results_object',detail:'API results payload is a JSON object.',passed:true}
        ]},
        warnings:[],
        recommendations:['Send the calendar invite with a short buffer before the meeting.'],
        failure_handling:[
            'If any downstream API fails, the UI can still render a structured response.',
            'Retry the request after restoring the backend connection.'
        ]
    }));
}
