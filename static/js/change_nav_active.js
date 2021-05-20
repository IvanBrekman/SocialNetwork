var nav = document.getElementsByClassName("nav-item nav-link")
page = document.location.pathname.substr(1, 3)
if (page == '') page = 'ind'

obj = document.getElementById(page)

for(var i = 0; i < nav.length; i++) {
    if(obj != nav[i]){
        nav[i].classList.remove('active')
        nav[i].style.color = "white"
    }
    else {
        obj.classList.add('active')
        obj.style.color = "black"
    }
}

if (page == 'dia') {
    document.getElementById('message_count').classList.remove('bg-secondary')
    document.getElementById('message_count').classList.add('bg-success')
} else {
    document.getElementById('message_count').classList.remove('bg-success')
    document.getElementById('message_count').classList.add('bg-secondary')
}
