function deletecomment(tag, mapid, commentid) {
  if(!confirm("Are you sure you want to delete this comment?"))
    return;
  callback = function(request) {
    comment_node = tag.parentNode.parentNode
    comment_node.parentNode.removeChild(comment_node);
  }  
  ajaxRequest("/" + mapid + "/deletecomment", "commentid="+commentid, callback);
  return false;
}

function clearflag(tag, mapid, commentid) {
  callback = function(request) {
    tag.parentNode.removeChild(tag);
  }
  url = "/" + mapid + "/clearflag";
  data = null;
  if(commentid != undefined)
    data = "commentid=" + commentid;
  ajaxRequest(url, data, callback);
  return false;
}
