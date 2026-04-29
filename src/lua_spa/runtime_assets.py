"""Client-side runtime used by the Lua SPA framework."""

SPA_RUNTIME_JS = r"""
(function () {
  "use strict";

  function readJsonScript(id) {
    var element = document.getElementById(id);
    if (!element || !element.textContent) {
      throw new Error("Missing bootstrap payload: " + id);
    }
    return JSON.parse(element.textContent);
  }

  function firstRenderableChild(container) {
    var child = container.firstChild;
    while (child) {
      if (child.nodeType === Node.ELEMENT_NODE) {
        return child;
      }
      if (child.nodeType === Node.TEXT_NODE && child.textContent && child.textContent.trim() !== "") {
        return child;
      }
      child = child.nextSibling;
    }
    return null;
  }

  function isIgnorableText(node) {
    return node.nodeType === Node.TEXT_NODE && (!node.textContent || node.textContent.trim() === "");
  }

  function normalizeDomChildren(node) {
    return Array.from(node.childNodes).filter(function (child) {
      return !isIgnorableText(child);
    });
  }

  function evaluateExpression(expression, context) {
    try {
      var evaluator = new Function("ctx", "with (ctx) { return (" + expression + "); }");
      var value = evaluator(context);
      return value == null ? "" : String(value);
    } catch (error) {
      console.warn("[lua-spa] expression failed:", expression, error);
      return "";
    }
  }

  function interpolate(template, context) {
    return template.replace(/{{\s*(.*?)\s*}}/g, function (_, expression) {
      return evaluateExpression(expression, context);
    });
  }

  function parseTemplate(template, context, registry) {
    var holder = document.createElement("template");
    holder.innerHTML = interpolate(template, context);
    var nodes = toVNodes(holder.content, context, registry);

    if (nodes.length === 0) {
      return { type: "text", text: "", el: null };
    }
    if (nodes.length === 1) {
      return nodes[0];
    }

    return {
      type: "element",
      tag: "div",
      props: {},
      events: {},
      children: nodes,
      el: null,
    };
  }

  function toVNodes(parent, context, registry) {
    return Array.from(parent.childNodes)
      .map(function (node) {
        return nodeToVNode(node, context, registry);
      })
      .filter(function (node) {
        return node !== null;
      });
  }

  function nodeToVNode(node, context, registry) {
    if (node.nodeType === Node.TEXT_NODE) {
      if (!node.textContent || node.textContent.trim() === "") {
        return null;
      }
      return {
        type: "text",
        text: node.textContent,
        el: null,
      };
    }

    if (node.nodeType !== Node.ELEMENT_NODE) {
      return null;
    }

    var tagName = node.tagName;
    if (Object.prototype.hasOwnProperty.call(registry, tagName)) {
      var componentProps = {};
      Array.from(node.attributes).forEach(function (attribute) {
        componentProps[attribute.name] = interpolate(attribute.value, context);
      });
      return {
        type: "component",
        name: tagName,
        props: componentProps,
        instance: null,
        el: null,
      };
    }

    var props = {};
    var events = {};
    Array.from(node.attributes).forEach(function (attribute) {
      if (attribute.name.indexOf("on:") === 0) {
        events[attribute.name.slice(3)] = attribute.value;
      } else {
        props[attribute.name] = interpolate(attribute.value, context);
      }
    });

    return {
      type: "element",
      tag: tagName.toLowerCase(),
      props: props,
      events: events,
      children: toVNodes(node, context, registry),
      el: null,
    };
  }

  function createApp(config, registry) {
    var app = {
      config: config,
      registry: registry,
      mount: function () {
        var container = document.getElementById(config.mountId);
        if (!container) {
          throw new Error("Mount point not found: #" + config.mountId);
        }

        var vnode = {
          type: "component",
          name: config.entry,
          props: config.props || {},
          instance: null,
          el: null,
        };

        var hydrationNode = firstRenderableChild(container);
        if (hydrationNode) {
          mountComponent(vnode, container, null, app, null, hydrationNode);
        } else {
          mount(vnode, container, null, app, null);
        }
      },
    };

    return app;
  }

  function compileSetup(script) {
    if (!script || script.trim() === "") {
      return null;
    }

    try {
      var factory = new Function(script + "\nreturn (typeof setup === 'function' ? setup : null);");
      return factory();
    } catch (error) {
      console.error("[lua-spa] component script compilation failed", error);
      return null;
    }
  }

  function createUseState(instance) {
    return function useState(initialValue) {
      var index = instance.hookCursor;
      instance.hookCursor += 1;

      if (!(index in instance.hooks)) {
        instance.hooks[index] = typeof initialValue === "function" ? initialValue() : initialValue;
      }

      function setState(nextValue) {
        var value = typeof nextValue === "function" ? nextValue(instance.hooks[index]) : nextValue;
        if (Object.is(value, instance.hooks[index])) {
          return;
        }
        instance.hooks[index] = value;
        instance.update();
      }

      return [instance.hooks[index], setState];
    };
  }

  function renderComponentSubtree(instance, app) {
    var componentDef = app.registry[instance.name];
    if (!componentDef) {
      throw new Error("Unknown component: " + instance.name);
    }

    instance.hookCursor = 0;
    var setupResult = {};
    if (instance.setup) {
      var result = instance.setup({
        useState: createUseState(instance),
        props: instance.props,
        state: instance.state,
        actions: instance.actions,
      });
      setupResult = result || {};
    }

    if (setupResult.state && typeof setupResult.state === "object") {
      instance.state = setupResult.state;
    }
    if (setupResult.actions && typeof setupResult.actions === "object") {
      instance.actions = setupResult.actions;
    }

    var context = {
      props: instance.props,
      state: instance.state,
      actions: instance.actions,
    };

    return parseTemplate(componentDef.template, context, app.registry);
  }

  function mount(vnode, container, anchor, app, currentComponent) {
    if (vnode.type === "text") {
      var textNode = document.createTextNode(vnode.text);
      vnode.el = textNode;
      container.insertBefore(textNode, anchor);
      return;
    }

    if (vnode.type === "element") {
      mountElement(vnode, container, anchor, app, currentComponent);
      return;
    }

    mountComponent(vnode, container, anchor, app, currentComponent, null);
  }

  function mountElement(vnode, container, anchor, app, currentComponent) {
    var el = document.createElement(vnode.tag);
    vnode.el = el;

    Object.keys(vnode.props).forEach(function (key) {
      setElementProp(el, key, vnode.props[key]);
    });

    patchElementEvents(el, {}, vnode.events, currentComponent);

    vnode.children.forEach(function (child) {
      mount(child, el, null, app, currentComponent);
    });

    container.insertBefore(el, anchor);
  }

  function mountComponent(vnode, container, anchor, app, parentComponent, hydrationNode) {
    var componentDef = app.registry[vnode.name];
    if (!componentDef) {
      throw new Error("Unknown component: " + vnode.name);
    }

    var instance = {
      name: vnode.name,
      props: vnode.props || {},
      hooks: [],
      hookCursor: 0,
      setup: compileSetup(componentDef.script),
      state: {},
      actions: {},
      subTree: null,
      isMounted: false,
      container: container,
      anchor: anchor,
      hydrationNode: hydrationNode,
      update: function () {
        var nextTree = renderComponentSubtree(instance, app);

        if (!instance.isMounted) {
          if (instance.hydrationNode) {
            hydrate(nextTree, instance.hydrationNode, instance.container, app, instance);
          } else {
            mount(nextTree, instance.container, instance.anchor, app, instance);
          }
          instance.isMounted = true;
          instance.subTree = nextTree;
          vnode.el = nextTree.el;
          return;
        }

        patch(instance.subTree, nextTree, instance.container, instance.anchor, app, instance);
        instance.subTree = nextTree;
        vnode.el = nextTree.el;
      },
    };

    vnode.instance = instance;
    instance.update();
  }

  function hydrate(vnode, existingNode, container, app, currentComponent) {
    if (!existingNode) {
      mount(vnode, container, null, app, currentComponent);
      return;
    }

    if (vnode.type === "text") {
      if (existingNode.nodeType !== Node.TEXT_NODE) {
        var freshText = document.createTextNode(vnode.text);
        container.replaceChild(freshText, existingNode);
        vnode.el = freshText;
        return;
      }
      if (existingNode.textContent !== vnode.text) {
        existingNode.textContent = vnode.text;
      }
      vnode.el = existingNode;
      return;
    }

    if (vnode.type === "component") {
      mountComponent(vnode, container, null, app, currentComponent, existingNode);
      return;
    }

    if (existingNode.nodeType !== Node.ELEMENT_NODE || existingNode.tagName.toLowerCase() !== vnode.tag) {
      var placeholder = existingNode.nextSibling;
      container.removeChild(existingNode);
      mount(vnode, container, placeholder, app, currentComponent);
      return;
    }

    vnode.el = existingNode;
    Object.keys(vnode.props).forEach(function (key) {
      setElementProp(existingNode, key, vnode.props[key]);
    });

    patchElementEvents(existingNode, {}, vnode.events, currentComponent);

    var domChildren = normalizeDomChildren(existingNode);
    var childCount = Math.max(domChildren.length, vnode.children.length);

    for (var index = 0; index < childCount; index += 1) {
      var domChild = domChildren[index] || null;
      var vChild = vnode.children[index] || null;

      if (!vChild && domChild) {
        existingNode.removeChild(domChild);
        continue;
      }

      if (vChild && !domChild) {
        mount(vChild, existingNode, null, app, currentComponent);
        continue;
      }

      if (vChild && domChild) {
        hydrate(vChild, domChild, existingNode, app, currentComponent);
      }
    }
  }

  function patch(previous, next, container, anchor, app, currentComponent) {
    if (!sameVNodeType(previous, next)) {
      var nextAnchor = previous.el ? previous.el.nextSibling : anchor;
      unmount(previous, container);
      mount(next, container, nextAnchor, app, currentComponent);
      return;
    }

    if (next.type === "text") {
      var textEl = previous.el;
      if (textEl && textEl.textContent !== next.text) {
        textEl.textContent = next.text;
      }
      next.el = textEl;
      return;
    }

    if (next.type === "component") {
      var instance = previous.instance;
      if (!instance) {
        mountComponent(next, container, anchor, app, currentComponent, null);
        return;
      }

      next.instance = instance;
      instance.props = next.props || {};
      instance.update();
      next.el = instance.subTree ? instance.subTree.el : null;
      return;
    }

    patchElement(previous, next, app, currentComponent);
  }

  function patchElement(previous, next, app, currentComponent) {
    var el = previous.el;
    next.el = el;

    patchProps(el, previous.props, next.props);
    patchElementEvents(el, previous.events, next.events, currentComponent);
    patchChildren(previous, next, el, app, currentComponent);
  }

  function patchChildren(previous, next, container, app, currentComponent) {
    var oldChildren = previous.children;
    var newChildren = next.children;

    var commonLength = Math.min(oldChildren.length, newChildren.length);
    for (var index = 0; index < commonLength; index += 1) {
      patch(oldChildren[index], newChildren[index], container, null, app, currentComponent);
    }

    if (newChildren.length > oldChildren.length) {
      for (var addIndex = commonLength; addIndex < newChildren.length; addIndex += 1) {
        mount(newChildren[addIndex], container, null, app, currentComponent);
      }
    }

    if (oldChildren.length > newChildren.length) {
      for (var removeIndex = commonLength; removeIndex < oldChildren.length; removeIndex += 1) {
        unmount(oldChildren[removeIndex], container);
      }
    }
  }

  function unmount(vnode, container) {
    if (vnode.type === "component") {
      if (vnode.instance && vnode.instance.subTree) {
        unmount(vnode.instance.subTree, container);
      }
      return;
    }

    if (!vnode.el || !vnode.el.parentNode) {
      return;
    }

    vnode.el.parentNode.removeChild(vnode.el);
  }

  function sameVNodeType(left, right) {
    if (!left || !right) {
      return false;
    }

    if (left.type !== right.type) {
      return false;
    }

    if (left.type === "element") {
      return left.tag === right.tag;
    }

    if (left.type === "component") {
      return left.name === right.name;
    }

    return true;
  }

  function patchProps(el, previous, next) {
    var prevProps = previous || {};
    var nextProps = next || {};

    Object.keys(nextProps).forEach(function (key) {
      if (prevProps[key] !== nextProps[key]) {
        setElementProp(el, key, nextProps[key]);
      }
    });

    Object.keys(prevProps).forEach(function (key) {
      if (!Object.prototype.hasOwnProperty.call(nextProps, key)) {
        el.removeAttribute(key);
      }
    });
  }

  function setElementProp(el, key, value) {
    if (value === false || value == null) {
      el.removeAttribute(key);
      return;
    }

    if (value === true) {
      el.setAttribute(key, "");
      return;
    }

    el.setAttribute(key, String(value));
  }

  function patchElementEvents(el, previous, next, currentComponent) {
    var listeners = el.__luaSpaListeners || {};
    var previousEvents = previous || {};
    var nextEvents = next || {};

    Object.keys(previousEvents).forEach(function (eventName) {
      if (!Object.prototype.hasOwnProperty.call(nextEvents, eventName) && listeners[eventName]) {
        el.removeEventListener(eventName, listeners[eventName]);
        delete listeners[eventName];
      }
    });

    Object.keys(nextEvents).forEach(function (eventName) {
      var actionName = nextEvents[eventName];
      var oldAction = previousEvents[eventName];

      if (oldAction === actionName && listeners[eventName]) {
        return;
      }

      if (listeners[eventName]) {
        el.removeEventListener(eventName, listeners[eventName]);
      }

      var nextListener = function (event) {
        if (!currentComponent || !currentComponent.actions) {
          return;
        }

        var action = currentComponent.actions[actionName];
        if (typeof action === "function") {
          action(event);
        }
      };

      listeners[eventName] = nextListener;
      el.addEventListener(eventName, nextListener);
    });

    el.__luaSpaListeners = listeners;
  }

  function bootstrap() {
    var registry = readJsonScript("lua-spa-registry");
    var config = readJsonScript("lua-spa-config");
    var app = createApp(config, registry);
    app.mount();
    return app;
  }

  window.LuaSpaRuntime = {
    bootstrap: bootstrap,
  };
})();
"""
