// Browser-agnostic factory function
function createXMLHttpRequest() {
  if (window.XMLHttpRequest) {
    return new XMLHttpRequest();
  } else if (window.ActiveXObject) {
    return new ActiveXObject('Microsoft.XMLHTTP')
  } else {
    return null;
  }
}

function ajaxRequest(url, content, callback) {
  request = createXMLHttpRequest();
  request.open("POST", url, true);
  fired = false;
  request.onreadystatechange = function() {
    if(request.readyState == 4) {
      if(request.status != 200) {
        alert("An error occurred processing your request. Please try again later.");
      } else if(!fired) {
        fired = true;
        callback(request);
      }
    }
  }
  request.setRequestHeader("Content-Type", "application/x-www-form-urlencoded");
  if(content == null) {
    request.send("");
  } else {
    request.send(content);
  }
}

// ----------------------------
// Tag suggestion functionality
// ----------------------------

var currentInput = null;
var request = null;
var currentDiv = null;

function getTags(tag) {
        var ret = '';
	var dialog = document.getElementById('tagdialog');
	for(var i = 0; i < dialog.childNodes.length; i++) {
		var nd = dialog.childNodes[i];
		if(nd.nodeName.toLowerCase() != 'input')
			continue;

		if(nd.value != '' && nd.value != null && nd != tag)
			ret = ret + nd.value + " ";
	}

	return ret;
}

function tagkeypress(tag, e) {
	var keynum;
	if(window.event) { //IE
		keynum = e.keyCode;
	} else { // everything else
		keynum = e.which;
	}
	tagchange(tag, tag.value + String.fromCharCode(keynum));
}

function tagchange(tag, prefix) {
	tagblur();

	currentInput = tag;
	request = createXMLHttpRequest();
	var tags = getTags(tag);

	var url = "/suggest_tags?count=10&tags="+tags+"&prefix="+prefix;
	request.open("GET", url , true);
	request.onreadystatechange = function() {
		if(request.readyState == 4 && request.status == 200) {
			var tagDialog = document.getElementById('tagdialog');
			currentDiv = document.createElement('div');
			currentDiv.innerHTML = request.responseText;
			currentDiv.childNodes[0].style.left = tag.offsetLeft + "px";
			currentDiv.childNodes[0].style.top = tag.offsetTop + tag.offsetHeight + "px";
			tagDialog.appendChild(currentDiv);
			request = null;
		}
	};
	request.send(null);
}

function tagblur() {
	var tagDialog = document.getElementById('tagdialog');
	currentInput = null;

	if(request != null) {
		request.abort();
		request = null;
	}

	if(currentDiv != null) {
		tagDialog.removeChild(currentDiv);
		currentDiv = null;
	}
}

function suggestclick(value) {
	currentInput.value = value;
	tagblur();
}

// -----------------------
// Favorites functionality
// -----------------------
function starclick(tag, mapid) {
  var imgtag = tag.getElementsByTagName("img")[0];
  starred = (imgtag.src.search(/unstarred.png$/) == -1);
  if(starred) {
    url = "/" + mapid + "/remstar";
  } else{
    url = "/" + mapid + "/addstar";
  }
  callback = function(request) {
    if(starred) {
      imgtag.src = "/static/unstarred.png";
    } else {
      imgtag.src = "/static/starred.png";
    }
  }
  ajaxRequest(url, null, callback);
  return false;
}

// -------------------
// Abuse reporting etc
// -------------------
function abusereport(tag, mapid, commentid) {
  callback = function(request) {
    txt = document.createTextNode("Reported for abuse");
    span = document.createElement("span");
    span.appendChild(txt);
    span.className = tag.className;
    tag.parentNode.replaceChild(span, tag);
  }
  url = "/" + mapid + "/reportabuse"
  data = null;
  if(commentid != undefined)
    data = "commentid=" + commentid;
  ajaxRequest(url, data, callback);
  return false;
}

// Image zooming
function setZoom(img, dir, width, height, zIndex, delay) {
  setTimeout(function() {
    if (img.dir==dir) {
      img.style.width = Math.floor(width) + "px";
      img.style.height = Math.floor(height) + "px";
      img.style.zIndex = zIndex;
    }
  }, delay);
}

function setThumb(img, dir, thumb, delay) {
  setfunc = function() {
    if(img.dir==dir) {
      var src = img.src.split("=")[0]
      if(thumb != "full") {
        src += "=s132";
      } else {
        src += "=s762";
      }
      img.src = src
    }
  }
  if(delay == 0) {
    setfunc();
  } else {
    setTimeout(setfunc, delay);
  }
}

function larger(img, width, height) {
  img.dir='rtl';
  now=parseInt(img.style.zIndex);
  s_w = img.width;
  s_h = img.height;
  steps = 20 - now;
  setThumb(img, 'rtl', "full", 0);
  for (i=0; i<=steps; i++) {
    w = s_w+(i*(width-s_w))/steps;
    h = s_h+(i*(height-s_h))/steps;
    setZoom(img, 'rtl', w, h, i, 20*i);
  }
}

function smaller(img, width, height) {
  img.dir = 'ltr';
  now = parseInt(img.style.zIndex);
  s_w = img.width;
  s_h = img.height;
  steps = now;
  for (i=now-1; i>=0; i--) {
    w = width + (i*(s_w-width))/steps;
    h = height + (i*(s_h-height))/steps;
    setZoom(img, 'ltr', w, h, i, 20*(now-i));
  }
  setThumb(img, 'ltr', "thumbs", 20*(now+1));
}

// feature queue rearranging

function swap_down(node) {
  const node1 = node.parentElement.parentElement;
  const node2 = node.parentElement.parentElement.nextElementSibling;
  const map_id_1 = node1.dataset.id;
  const map_id_2 = node2.dataset.id;

  const callback = function (response) {
    node1.parentNode.replaceChild(node1, node2);
    node1.parentNode.insertBefore(node2, node1);
  }

  url = "/" + map_id_1 + "/swap"
  data = "other_map_id=" + map_id_2;
  ajaxRequest(url, data, callback);
  return false;
}

function swap_up(node) {
  const node1 = node.parentElement.parentElement.previousElementSibling;
  const node2 = node.parentElement.parentElement;
  const map_id_1 = node1.dataset.id;
  const map_id_2 = node2.dataset.id;

  const callback = function (response) {
    debugger
    node1.parentNode.replaceChild(node1, node2);
    node1.parentNode.insertBefore(node2, node1);
  }

  url = "/" + map_id_2 + "/swap"
  data = "other_map_id=" + map_id_1;
  ajaxRequest(url, data, callback);
  return false;
}
